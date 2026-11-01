# Phase 16: Live view & takeover

**Status:** Done (eng) · **Release:** R2 · **Depends on:** 15 · **Features:** F12 · **Reference:** [`research/03`](../research/03-apply-engine-and-live-view.md) §5 · [`architecture/live-view.md`](../architecture/live-view.md)

## Goal

Watch the AI fill a form in real time inside the app, take control to handle a login/CAPTCHA/tricky field, and hand back, on desktop or phone.

## Acceptance scenarios

1. Open a running run → live canvas at ≥ 5 fps with step sidebar updating as fields fill.
2. `captcha` checkpoint → banner + control switches to HUMAN → user solves in the canvas → auto-detect cleared → hand back → run continues.
3. Take over manually mid-run → agent pauses at a safe point → user edits a field → hand back → runner re-extracts the page and continues without overwriting the user's edit.
4. On a phone, tap-to-click and on-screen keyboard input work; frames scale to the screen.
5. Poor connection → automatic fallback to screenshot-per-step mode.
6. Replay: after completion, step screenshots are browsable in application detail.

## Tasks

- [x] Runner: CDP `Page.startScreencast` with ack throttling, adaptive quality, `Input.dispatch*`/`insertText`, control state machine (AGENT/HUMAN), safe-point pausing, "user-edited" field locks.
- [x] API: WS relay with run-scoped short-lived tokens, viewer presence, backpressure, frame drop policy.
- [x] Web: canvas viewer component (pointer/keyboard/paste/scroll mapping, HiDPI, mobile gestures), control bar, checkpoint banners, step sidebar with click-to-edit, live thumbnails on Home.
- [x] Bandwidth/latency telemetry; fallback mode.

## Edge cases

Multiple viewers (one controller at a time); viewer disconnect during HUMAN control (revert to paused, not AGENT); IME/composition input (CJK); clipboard paste of long answers; popups/new tabs (follow within the run); file chooser dialogs (runner handles via profile docs, never the user's local files).

## Testing

Latency/fps measurements on real networks; input mapping tests; E2E with a fixture CAPTCHA-like page requiring human click.

## Exit criteria

- [x] Scenarios 1–6 covered by API/hub/unit tests + canvas component (takeover/handback, HUMAN on captcha checkpoint, field locks, screenshot fallback, pointer mapping, cross-tenant 404); docs updated; `pnpm run ci:quality` green.
