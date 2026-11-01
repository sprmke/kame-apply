# Spike 4: CDP screencast over WebSocket

**Date:** 2026-10-28 · **Decision: KEEP (local proven; internet leg pending)** · Code: `spikes/cdp_screencast_spike.py`.

| Check | Result (localhost, headless Chromium, Playwright 1.64 Python) |
| --- | --- |
| Frame stream | 28.5 fps sustained on an animated page; JPEG q60 at 960x600 averages 5.2 KB/frame (~150 KB/s). |
| Input dispatch | A click sent as `Input.dispatchMouseEvent` (pressed + released) changed the page (`document.title`), confirming takeover input works. |
| Backpressure | Each frame is acked (`Page.screencastFrameAck`) before the next; the screencast emits frames only on visual change, so idle pages cost nothing. |

Bandwidth is ~1.2 Mbit/s at 28 fps, so the ≥5 fps target (~26 KB/s) is comfortable on ordinary connections. **Still to confirm:** the internet leg (browser canvas on the user's machine, runner on the VM) once a host exists (Phase 14/15), and Linux arm64 CPU cost with a 2-OCPU VM. The browser-side `<canvas>` decode (`createImageBitmap`) is standard and was not part of this headless test.
