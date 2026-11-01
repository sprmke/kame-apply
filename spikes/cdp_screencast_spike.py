"""Spike: Playwright (Python) -> CDP Page.startScreencast -> WebSocket -> client, plus input dispatch.

Server streams JPEG frames; client counts fps and sends a click that is dispatched with
Input.dispatchMouseEvent. Run: python spikes/cdp_screencast_spike.py (needs playwright, websockets).
"""

import asyncio
import base64
import json
import time

import websockets
from playwright.async_api import async_playwright

PAGE = """<!doctype html><title>idle</title>
<button id=b style="position:absolute;left:100px;top:100px;width:200px;height:80px"
 onclick="document.title='clicked';document.body.style.background='#f60'">go</button>
<div id=t style="position:absolute;left:400px;top:100px;font:40px monospace"></div><script>let n=0;setInterval(()=>{document.getElementById('t').textContent=++n;},33)</script>"""


async def serve(ws):
    async with async_playwright() as p:
        browser = await p.chromium.launch()
        page = await browser.new_page(viewport={"width": 960, "height": 600})
        await page.set_content(PAGE)
        cdp = await page.context.new_cdp_session(page)

        async def on_frame(params):
            await cdp.send("Page.screencastFrameAck", {"sessionId": params["sessionId"]})
            await ws.send(base64.b64decode(params["data"]))

        cdp.on("Page.screencastFrame", lambda params: asyncio.create_task(on_frame(params)))
        await cdp.send(
            "Page.startScreencast",
            {"format": "jpeg", "quality": 60, "maxWidth": 960, "maxHeight": 600, "everyNthFrame": 1},
        )
        async for raw in ws:
            msg = json.loads(raw)
            if msg["type"] == "click":
                for t in ("mousePressed", "mouseReleased"):
                    await cdp.send(
                        "Input.dispatchMouseEvent",
                        {"type": t, "x": msg["x"], "y": msg["y"], "button": "left", "clickCount": 1},
                    )
                await asyncio.sleep(0.2)
                await ws.send(json.dumps({"type": "title", "value": await page.title()}))
            elif msg["type"] == "stop":
                break
        await cdp.send("Page.stopScreencast")
        await browser.close()


async def main() -> None:
    async with websockets.serve(serve, "127.0.0.1", 8765):
        async with websockets.connect("ws://127.0.0.1:8765", max_size=8_000_000) as c:
            frames, bytes_, t0 = 0, 0, time.time()
            clicked = False
            title = None
            while time.time() - t0 < 6:
                try:
                    m = await asyncio.wait_for(c.recv(), 1)
                except TimeoutError:
                    continue
                if isinstance(m, bytes):
                    frames += 1
                    bytes_ += len(m)
                else:
                    title = json.loads(m)["value"]
                # Screencast only emits frames on visual change, so trigger the click by time.
                if not clicked and time.time() - t0 > 3:
                    await c.send(json.dumps({"type": "click", "x": 150, "y": 130}))
                    clicked = True
            dt = time.time() - t0
            await c.send(json.dumps({"type": "stop"}))
            print(f"frames={frames} fps={frames / dt:.1f} avg_frame={bytes_ / max(frames, 1) / 1024:.1f}KB title_after_click={title}")
            assert title == "clicked", "click dispatch failed"
            print("CDP SPIKE OK")


asyncio.run(main())
