"""CDP screencast + input dispatch + control state for live view."""

from __future__ import annotations

import asyncio
import base64
import json
import logging
from collections.abc import Awaitable, Callable
from typing import Any

import httpx
from playwright.async_api import CDPSession, Page

log = logging.getLogger("kame.runner.live")

ControlMode = str  # agent | human | paused


class LiveSession:
    """Owns CDP screencast and optional WS to the API relay."""

    def __init__(
        self,
        *,
        page: Page,
        api_base: str,
        token: str,
        workspace_id: str,
        run_id: str,
        headers: dict[str, str],
    ) -> None:
        self.page = page
        self.api_base = api_base.rstrip("/")
        self.token = token
        self.workspace_id = workspace_id
        self.run_id = run_id
        self.headers = headers
        self.control_mode: ControlMode = "agent"
        self.live_mode = "screencast"
        self.quality = 60
        self.max_width = 1280
        self.seq = 0
        self._cdp: CDPSession | None = None
        self._ws = None
        self._task: asyncio.Task | None = None
        self._human_event = asyncio.Event()
        self._human_event.set()  # agent may proceed
        self.user_edited: set[str] = set()
        self._on_reextract: Callable[[], Awaitable[None]] | None = None

    def set_reextract_handler(self, fn: Callable[[], Awaitable[None]]) -> None:
        self._on_reextract = fn

    async def start(self) -> None:
        # Mint runner live token (sync httpx off the event loop)
        def _mint() -> httpx.Response:
            return httpx.post(
                f"{self.api_base}/api/v1/runs/{self.run_id}/live/runner-token",
                headers=self.headers,
                timeout=30.0,
            )

        r = await asyncio.to_thread(_mint)
        if r.status_code >= 400:
            log.warning("live_token_failed status=%s", r.status_code)
            return
        live_token = r.json()["token"]
        ws_path = r.json()["ws_path"]
        base = self.api_base.replace("https://", "wss://").replace("http://", "ws://")
        ws_url = f"{base}{ws_path}?token={live_token}"

        try:
            import websockets
        except ImportError:
            log.warning("websockets not installed; live view disabled")
            return

        self._cdp = await self.page.context.new_cdp_session(self.page)
        self._cdp.on(
            "Page.screencastFrame",
            lambda params: asyncio.create_task(self._on_frame(params)),
        )
        await self._start_screencast()

        self._ws = await websockets.connect(ws_url, max_size=8_000_000)
        await self._ws.send(
            json.dumps(
                {"type": "state", "control_mode": self.control_mode, "live_mode": self.live_mode}
            )
        )
        self._task = asyncio.create_task(self._recv_loop())

    async def _start_screencast(self) -> None:
        if not self._cdp:
            return
        await self._cdp.send(
            "Page.startScreencast",
            {
                "format": "jpeg",
                "quality": self.quality,
                "maxWidth": self.max_width,
                "maxHeight": 900,
                "everyNthFrame": 1,
            },
        )

    async def _on_frame(self, params: dict[str, Any]) -> None:
        if not self._cdp:
            return
        try:
            await self._cdp.send("Page.screencastFrameAck", {"sessionId": params["sessionId"]})
        except Exception:
            return
        if self.live_mode == "off" or self._ws is None:
            return
        if self.live_mode == "screenshot":
            # Screencast still runs but we don't push every frame; runner pushes on step.
            return
        self.seq += 1
        msg = {
            "type": "frame",
            "seq": self.seq,
            "data": params["data"],
            "metadata": params.get("metadata") or {},
            "quality": self.quality,
        }
        try:
            await self._ws.send(json.dumps(msg))
        except Exception:
            log.debug("frame_send_failed", exc_info=True)

    async def push_screenshot(self) -> None:
        if self._ws is None:
            return
        png = await self.page.screenshot(type="jpeg", quality=self.quality)
        self.seq += 1
        await self._ws.send(
            json.dumps(
                {
                    "type": "screenshot",
                    "seq": self.seq,
                    "data": base64.b64encode(png).decode("ascii"),
                    "mode": "screenshot",
                }
            )
        )

    async def _recv_loop(self) -> None:
        assert self._ws is not None
        try:
            async for raw in self._ws:
                if isinstance(raw, bytes):
                    continue
                msg = json.loads(raw)
                await self._handle(msg)
        except Exception:
            log.info("live_ws_closed")

    async def _handle(self, msg: dict[str, Any]) -> None:
        typ = msg.get("type")
        if typ == "control":
            mode = msg.get("mode") or "agent"
            self.control_mode = mode
            if mode == "human" or mode == "paused":
                self._human_event.clear()
            else:
                self._human_event.set()
                if msg.get("reextract") and self._on_reextract:
                    await self._on_reextract()
            return
        if typ == "mode":
            self.live_mode = msg.get("live_mode") or self.live_mode
            if self.live_mode == "screencast" and self.quality < 40:
                self.quality = 40
            if self.live_mode == "screenshot":
                self.quality = 40
                self.max_width = 960
            return
        if typ in {"input", "mouse", "key", "text", "scroll", "paste"}:
            await self._dispatch_input(msg)
            field_id = msg.get("field_id")
            if field_id:
                self.user_edited.add(str(field_id))

    async def _dispatch_input(self, msg: dict[str, Any]) -> None:
        if not self._cdp or self.control_mode != "human":
            return
        kind = msg.get("kind") or msg.get("type")
        if kind in {"mouse", "input"} and "x" in msg:
            for t in ("mousePressed", "mouseReleased"):
                await self._cdp.send(
                    "Input.dispatchMouseEvent",
                    {
                        "type": t,
                        "x": float(msg["x"]),
                        "y": float(msg["y"]),
                        "button": msg.get("button") or "left",
                        "clickCount": 1,
                    },
                )
        elif kind == "scroll":
            await self._cdp.send(
                "Input.dispatchMouseEvent",
                {
                    "type": "mouseWheel",
                    "x": float(msg.get("x") or 0),
                    "y": float(msg.get("y") or 0),
                    "deltaX": float(msg.get("deltaX") or 0),
                    "deltaY": float(msg.get("deltaY") or 0),
                },
            )
        elif kind in {"key", "text", "paste"}:
            text = msg.get("text") or msg.get("value") or ""
            if text:
                # Sensitive keystrokes are not logged (live-view skill).
                await self._cdp.send("Input.insertText", {"text": text})

    async def wait_if_human(self) -> None:
        """Block the page loop while HUMAN/paused has control."""
        await self._human_event.wait()

    def should_skip_field(self, field_id: str) -> bool:
        return field_id in self.user_edited

    async def notify_human_for_checkpoint(self) -> None:
        self.control_mode = "human"
        self._human_event.clear()
        if self._ws:
            await self._ws.send(
                json.dumps({"type": "state", "control_mode": "human", "live_mode": self.live_mode})
            )

    async def close(self) -> None:
        if self._cdp:
            try:
                await self._cdp.send("Page.stopScreencast")
            except Exception:  # noqa: S110
                pass
        if self._task:
            self._task.cancel()
        if self._ws:
            try:
                await self._ws.close()
            except Exception:  # noqa: S110
                pass


def map_pointer_to_page(
    *,
    canvas_x: float,
    canvas_y: float,
    canvas_w: float,
    canvas_h: float,
    page_w: float,
    page_h: float,
) -> tuple[float, float]:
    """Map canvas CSS pixels to page coordinates (HiDPI-aware caller supplies CSS size)."""
    if canvas_w <= 0 or canvas_h <= 0:
        return canvas_x, canvas_y
    return canvas_x / canvas_w * page_w, canvas_y / canvas_h * page_h
