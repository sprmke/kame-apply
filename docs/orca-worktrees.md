# Orca worktrees

Each Orca worktree runs its own Nuxt web app on a sticky port. The Python API
on `:8100` and its Docker Postgres stay shared.

## Ports

| Checkout | Port |
| --- | --- |
| Primary checkout | `3100` |
| Other Orca worktrees | Sticky `3600`-`3699` |

```bash
bun run ui          # this worktree's web app, writes .local/vite-port
bun run ui:port     # print the port only
```

## Orca setup

Repo root [`orca.yaml`](../orca.yaml):

- `scripts.setup` → `pnpm install` + copy `apps/api/.env` from `ORCA_ROOT_PATH`
- `defaultTabs` → opens a **UI** tab that runs `bun run ui`
- `scripts.archive` → stops only this worktree's Nuxt server

In Orca: **Settings → Projects → kame-apply → Worktree hooks → Advanced →
Command source** → **orca.yaml only**.

Start the shared backend once with `./dev.sh` (Docker Postgres + API on `:8100`).
A worktree's UI tab starts only the web app.

## Local sign-in

There is no seeded local test user in this repo. Use the account configured in
`apps/api/.env` against the shared local API. OAuth callbacks must be registered
for the port you use.

## Verify

1. `./dev.sh` once, then `bun run ui` in the worktree.
2. Open the printed URL and sign in with the configured account.
3. Jobs, sources, and taxonomy pages load from the shared API.
