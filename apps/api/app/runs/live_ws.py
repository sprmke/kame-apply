"""WebSocket endpoints for live-view relay."""

from __future__ import annotations

import logging
from typing import Any
from uuid import UUID

from fastapi import APIRouter, WebSocket, WebSocketDisconnect
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from app.core.config import Settings
from app.core.rbac import can
from app.core.rls import set_request_context
from app.extension.models import ApplyRun
from app.runs.live_hub import get_live_hub
from app.runs.live_tokens import decode_live_token

log = logging.getLogger(__name__)
router = APIRouter(tags=["live-view"])

# Messages that change the page or control the run. Read-only roles may watch, never act.
CONTROL_MESSAGES = frozenset(
    {"takeover", "handback", "input", "mouse", "key", "text", "scroll", "paste"}
)


@router.websocket("/runs/{run_id}/live")
async def live_view_ws(websocket: WebSocket, run_id: UUID) -> None:
    token = websocket.query_params.get("token") or ""
    settings: Settings = websocket.app.state.settings
    session_factory: async_sessionmaker[AsyncSession] = websocket.app.state.session_factory

    try:
        claims = decode_live_token(settings, token)
    except Exception:
        await websocket.close(code=4401)
        return

    if claims["run_id"] != run_id:
        await websocket.close(code=4403)
        return

    role = claims["role"]
    workspace_id = claims["workspace_id"]
    user_id = claims["user_id"]

    # Confirm the caller is still an active member and the run exists in that workspace (RLS).
    async with session_factory() as session:
        await set_request_context(session, user_id=str(user_id), workspace_id=str(workspace_id))
        membership = (
            await session.execute(
                text(
                    "SELECT 1 FROM workspace_members m JOIN users u ON u.id = m.user_id "
                    "AND u.is_active WHERE m.workspace_id = :w AND m.user_id = :u "
                    "AND m.is_active"
                ),
                {"w": workspace_id, "u": user_id},
            )
        ).first()
        if membership is None:
            await websocket.close(code=4403)
            return
        run = await session.get(ApplyRun, run_id)
        if run is None or run.workspace_id != workspace_id:
            await websocket.close(code=4404)
            return
        control_mode = run.control_mode
        live_mode = run.live_mode if run.live_mode != "off" else "screencast"

    await websocket.accept()
    hub = get_live_hub()
    room = await hub.join(
        run_id=run_id,
        workspace_id=workspace_id,
        ws=websocket,
        role=role,
        user_id=user_id,
    )
    async with room.lock:
        room.control_mode = control_mode
        if room.live_mode == "off":
            room.live_mode = live_mode

    await websocket.send_json(
        {
            "type": "hello",
            "role": role,
            "control_mode": room.control_mode,
            "live_mode": room.live_mode,
            "run_id": str(run_id),
        }
    )

    try:
        while True:
            raw = await websocket.receive_json()
            await _handle_message(
                room=room,
                role=role,
                user_id=user_id,
                msg=raw,
                session_factory=session_factory,
                workspace_id=workspace_id,
            )
    except WebSocketDisconnect:
        pass
    except Exception:
        log.exception("live_ws_error run=%s role=%s", run_id, role)
    finally:
        await hub.leave(room, websocket)


async def _handle_message(
    *,
    room: Any,
    role: str,
    user_id: UUID,
    msg: dict[str, Any],
    session_factory: async_sessionmaker[AsyncSession],
    workspace_id: UUID,
) -> None:
    hub = get_live_hub()
    typ = msg.get("type")

    if role == "runner":
        if typ == "frame":
            await hub.relay_frame(room, msg)
            return
        if typ == "screenshot":
            await hub.relay_frame(room, {**msg, "type": "frame", "mode": "screenshot"})
            return
        if typ == "state":
            async with room.lock:
                if "control_mode" in msg:
                    room.control_mode = msg["control_mode"]
                if "live_mode" in msg:
                    room.live_mode = msg["live_mode"]
                if "fps" in msg:
                    room.fps_ema = float(msg["fps"] or 0)
            await hub.broadcast_presence(room)
            # Persist light telemetry
            async with session_factory() as session:
                await set_request_context(
                    session, user_id=str(user_id), workspace_id=str(workspace_id)
                )
                run = await session.get(ApplyRun, room.run_id)
                if run:
                    run.live_telemetry = {
                        **(run.live_telemetry or {}),
                        "fps": room.fps_ema,
                        "drops": room.drop_count,
                        "live_mode": room.live_mode,
                    }
                    if "control_mode" in msg:
                        run.control_mode = msg["control_mode"]
                    if "live_mode" in msg:
                        run.live_mode = msg["live_mode"]
                    await session.commit()
            return
        if typ == "step":
            await hub._fanout(room, msg, include_runner=False)
            return
        return

    # Viewer messages
    if role != "runner" and typ in CONTROL_MESSAGES and not can(role, "data.write"):
        await hub._fanout(
            room,
            {"type": "error", "code": "read_only"},
            include_runner=False,
        )
        return

    if typ == "ack":
        seq = int(msg.get("seq") or 0)
        for v in room.viewers:
            if v.user_id == user_id:
                v.last_ack_seq = max(v.last_ack_seq, seq)
                break
        return

    if typ == "takeover":
        async with room.lock:
            if (
                room.control_mode == "human"
                and room.controller_user_id is not None
                and room.controller_user_id != user_id
            ):
                return
            room.control_mode = "human"
            room.controller_user_id = user_id
        async with session_factory() as session:
            await set_request_context(session, user_id=str(user_id), workspace_id=str(workspace_id))
            run = await session.get(ApplyRun, room.run_id)
            if run:
                run.control_mode = "human"
                run.controller_user_id = user_id
                if run.live_mode == "off":
                    run.live_mode = "screencast"
                await session.commit()
        await hub.send_to_runner(
            room, {"type": "control", "mode": "human", "controller_user_id": str(user_id)}
        )
        await hub.broadcast_presence(room)
        return

    if typ == "handback":
        async with room.lock:
            if room.controller_user_id not in (None, user_id):
                return
            room.control_mode = "agent"
            room.controller_user_id = None
        async with session_factory() as session:
            await set_request_context(session, user_id=str(user_id), workspace_id=str(workspace_id))
            run = await session.get(ApplyRun, room.run_id)
            if run:
                run.control_mode = "agent"
                run.controller_user_id = None
                await session.commit()
        await hub.send_to_runner(room, {"type": "control", "mode": "agent", "reextract": True})
        await hub.broadcast_presence(room)
        return

    if typ in {"input", "mouse", "key", "text", "scroll", "paste"}:
        ok = await hub.relay_input(room, msg, from_user=user_id)
        if not ok:
            await hub._fanout(
                room,
                {"type": "error", "code": "not_controller"},
                include_runner=False,
            )
        # Lock field if provided
        field_id = msg.get("field_id")
        if ok and field_id:
            async with session_factory() as session:
                await set_request_context(
                    session, user_id=str(user_id), workspace_id=str(workspace_id)
                )
                run = await session.get(ApplyRun, room.run_id)
                if run:
                    locks = list(run.user_edited_fields or [])
                    if not any(
                        isinstance(x, dict) and x.get("field_id") == field_id for x in locks
                    ):
                        locks.append({"field_id": field_id, "label": msg.get("label") or field_id})
                        run.user_edited_fields = locks
                        await session.commit()
        return
