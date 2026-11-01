---
name: live-view
description: CDP screencast relay and human takeover protocol for the runner. Phase 16.
---

# Live view

Read `docs/research/03-apply-engine-and-live-view.md` and `docs/phases/phase-16-live-view-and-takeover.md`.

- Runner: CDP `Page.startScreencast` → frames over WebSocket to the API relay → `<canvas>` in the web app. Input flows back through `Input.dispatchMouseEvent` / `dispatchKeyEvent`.
- **Control state**: `AGENT | HUMAN`. Takeover pauses the loop at a safe point; "Hand back" re-extracts the page and continues. Checkpoints switch control to HUMAN automatically.
- Relay is workspace-scoped and authenticated per session; frames are not persisted; screenshots for the step log are separate, redacted for sensitive fields.
- Backpressure: drop frames, cap fps and size; reconnect resumes from current frame.
- Accessibility: a text step log mirrors the canvas; control pill is keyboard operable.
- Human actions in takeover are the user's own; do not instrument them to mimic or evade detection.
