# What remains after eng phases 0–20

Engineering for the build plan is complete. Items below are **operator / human / time-gated**, not missing code.

| Item | Phase | Unblocks with |
| --- | --- | --- |
| First prod bring-up (VM, DNS, TLS, migrate) | 14 | `applywave` in the same message as the deploy/migrate request |
| Free uptime monitor on `/healthz` | 14 | After prod URL exists |
| Dogfood log (2 weeks, ≥3 tracks, ≥20 tailored apps) | 14 | Real job search on prod |
| PRD success-metric baselines | 14 | Dogfood data |
| Live `AUTO_SUBMIT_ENABLED` | 19 | Gate metrics + `applywave` |
| A1 memory re-measure / CDP internet | 1 spike 02 | First host (Oracle or Hetzner) |
| Owner dogfood notes on matching / tailor / agent bridge | 6, 9, 12b | Personal use |
| Deferred ATS/source adapters, retention compression, mobile swipe | 5–6 | Later backlog, not R1 blockers |

Canonical deploy checklist: [`../architecture/deployment.md`](../architecture/deployment.md) §5–operator notes in [`phase-14-r1-hardening-and-launch.md`](./phase-14-r1-hardening-and-launch.md).

