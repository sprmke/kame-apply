"""In-process live-view WebSocket relay (one controller, many viewers)."""

from __future__ import annotations

import asyncio
import logging
import time
from dataclasses import dataclass, field
from typing import Any
from uuid import UUID

from fastapi import WebSocket

log = logging.getLogger(__name__)


@dataclass
class LivePeer:
    ws: WebSocket
    role: str  # viewer | runner
    user_id: UUID | None
    last_ack_seq: int = 0
    last_frame_at: float = 0.0


@dataclass
class LiveRoom:
    run_id: UUID
    workspace_id: UUID
    runner: LivePeer | None = None
    viewers: list[LivePeer] = field(default_factory=list)
    control_mode: str = "agent"  # agent | human | paused
    controller_user_id: UUID | None = None
    live_mode: str = "screencast"  # screencast | screenshot | off
    last_frame_seq: int = 0
    fps_ema: float = 0.0
    drop_count: int = 0
    lock: asyncio.Lock = field(default_factory=asyncio.Lock)

    def viewer_count(self) -> int:
        return len(self.viewers)


class LiveHub:
    def __init__(self) -> None:
        self._rooms: dict[UUID, LiveRoom] = {}
        self._lock = asyncio.Lock()

    async def room(self, run_id: UUID, workspace_id: UUID) -> LiveRoom:
        async with self._lock:
            r = self._rooms.get(run_id)
            if r is None:
                r = LiveRoom(run_id=run_id, workspace_id=workspace_id)
                self._rooms[run_id] = r
            return r

    async def join(
        self,
        *,
        run_id: UUID,
        workspace_id: UUID,
        ws: WebSocket,
        role: str,
        user_id: UUID | None,
    ) -> LiveRoom:
        room = await self.room(run_id, workspace_id)
        peer = LivePeer(ws=ws, role=role, user_id=user_id)
        async with room.lock:
            if role == "runner":
                if room.runner is not None:
                    try:
                        await room.runner.ws.close(code=4000)
                    except Exception:  # noqa: S110
                        pass
                room.runner = peer
            else:
                room.viewers.append(peer)
        await self.broadcast_presence(room)
        return room

    async def leave(self, room: LiveRoom, ws: WebSocket) -> None:
        async with room.lock:
            was_controller = False
            if room.runner and room.runner.ws is ws:
                room.runner = None
            else:
                before = len(room.viewers)
                room.viewers = [v for v in room.viewers if v.ws is not ws]
                left = before - len(room.viewers)
                if left and room.controller_user_id:
                    # If controller disconnected while HUMAN → paused, not AGENT.
                    for v in list(room.viewers):
                        if v.user_id == room.controller_user_id:
                            break
                    else:
                        was_controller = room.control_mode == "human"
                        if was_controller:
                            room.control_mode = "paused"
                            room.controller_user_id = None
        await self.broadcast_presence(room)
        if was_controller:
            await self.send_to_runner(
                room, {"type": "control", "mode": "paused", "reason": "controller_disconnect"}
            )

    async def broadcast_presence(self, room: LiveRoom) -> None:
        msg = {
            "type": "presence",
            "viewers": room.viewer_count(),
            "control_mode": room.control_mode,
            "controller_user_id": str(room.controller_user_id) if room.controller_user_id else None,
            "live_mode": room.live_mode,
            "fps": round(room.fps_ema, 1),
            "drops": room.drop_count,
        }
        await self._fanout(room, msg, include_runner=True)

    async def relay_frame(self, room: LiveRoom, msg: dict[str, Any]) -> None:
        """Runner → viewers. Drop for slow viewers (backpressure)."""
        seq = int(msg.get("seq") or 0)
        room.last_frame_seq = max(room.last_frame_seq, seq)
        now = time.monotonic()
        # crude fps EMA
        if room.fps_ema <= 0:
            room.fps_ema = 5.0
        else:
            room.fps_ema = 0.8 * room.fps_ema + 0.2 * min(30.0, 1.0 / max(0.001, 0.05))

        dead: list[LivePeer] = []
        for v in list(room.viewers):
            # If viewer is >2 frames behind, drop this frame for them
            if seq - v.last_ack_seq > 2 and v.last_ack_seq > 0:
                room.drop_count += 1
                continue
            try:
                await v.ws.send_json(msg)
                v.last_frame_at = now
            except Exception:
                dead.append(v)
        for d in dead:
            await self.leave(room, d.ws)

        # Adaptive: if many drops, tell runner to lower quality / screenshot mode
        if room.drop_count >= 20 and room.live_mode == "screencast":
            room.live_mode = "screenshot"
            room.drop_count = 0
            await self.send_to_runner(room, {"type": "mode", "live_mode": "screenshot"})
            await self.broadcast_presence(room)

    async def relay_input(self, room: LiveRoom, msg: dict[str, Any], from_user: UUID) -> bool:
        """Viewer input → runner. Only controller may send while HUMAN."""
        if room.control_mode != "human":
            return False
        if room.controller_user_id and room.controller_user_id != from_user:
            return False
        return await self.send_to_runner(room, msg)

    async def send_to_runner(self, room: LiveRoom, msg: dict[str, Any]) -> bool:
        if room.runner is None:
            return False
        try:
            await room.runner.ws.send_json(msg)
            return True
        except Exception:
            return False

    async def _fanout(self, room: LiveRoom, msg: dict[str, Any], *, include_runner: bool) -> None:
        targets: list[LivePeer] = list(room.viewers)
        if include_runner and room.runner:
            targets.append(room.runner)
        dead: list[WebSocket] = []
        for p in targets:
            try:
                await p.ws.send_json(msg)
            except Exception:
                dead.append(p.ws)
        for ws in dead:
            await self.leave(room, ws)

    def get(self, run_id: UUID) -> LiveRoom | None:
        return self._rooms.get(run_id)


_hub: LiveHub | None = None


def get_live_hub() -> LiveHub:
    global _hub
    if _hub is None:
        _hub = LiveHub()
    return _hub
