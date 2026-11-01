# Live view & takeover (Phase 16)

Watch a runner fill a form in real time, take control for login/CAPTCHA/tricky fields, and hand back.

## Protocol

| Call | Who | Purpose |
| --- | --- | --- |
| `POST /api/v1/runs/{id}/live/token` | member | Short-lived viewer JWT (`typ=live_view`) |
| `POST /api/v1/runs/{id}/live/runner-token` | runner | Short-lived runner JWT |
| `WS /api/v1/runs/{id}/live?token=` | viewer / runner | Frame + input relay |
| `POST /api/v1/runs/{id}/live/takeover` | member | `control_mode=human` |
| `POST /api/v1/runs/{id}/live/handback` | controller | `control_mode=agent` + re-extract |
| `PATCH /api/v1/runs/{id}/live/mode` | member | `screencast` \| `screenshot` \| `off` |
| `GET /api/v1/runs/{id}/live/state` | member | Presence + telemetry |
| `POST /api/v1/runs/{id}/live/field-lock` | runner | Mark user-edited field |

## Control state

`agent` → runner fills. `human` → one controller; agent loop waits at a safe point. `paused` → controller disconnected mid-HUMAN (does not auto-resume to agent).

Open checkpoints set `human` automatically. Resolve returns to `agent`.

## Frames

Runner CDP `Page.startScreencast` → JPEG frames over WS. Viewers ack by `seq`. Slow clients drop frames; sustained drops flip `live_mode` to `screenshot`.

## Security

Run-scoped tokens expire in minutes. Sensitive keystrokes in HUMAN mode are not logged. Frames are not persisted; step screenshots are separate and PII-blurred.
