# Screenshots

Portfolio images for the main [README](../../README.md). Sourced from design captures under [`docs/design/screenshots/`](../design/screenshots/) (1440px, light).

| File | View |
| --- | --- |
| `sign-in.png` | Auth / sign-in |
| `today.png` | Today command center |
| `tracks.png` | Tracks list |
| `track-criteria.png` | Track criteria builder |
| `track-settings.png` | Track sources & autonomy |
| `jobs.png` | Jobs research board |
| `profile.png` | Career Profile |
| `studio.png` | Resume Studio |
| `applications-board.png` | Applications kanban |
| `applications-table.png` | Applications table |
| `answer-desk.png` | Answer Desk |
| `safety.png` | Safety / flagged jobs |
| `notifications.png` | Notification center |

Regenerate phase captures with the local stack running:

```bash
pnpm run dev
CAPTURE=1 CAPTURE_PHASE=11 pnpm exec playwright test e2e/capture-screens.spec.ts
```

Then re-copy the chosen `*-1440-light.png` files into this folder with the names above.
