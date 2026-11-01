# ka-start-app

Start the local Kame Apply stack (target shape; commands land in Phase 1, check `package.json`).

```bash
pnpm run dev:docker   # Postgres+pgvector, MinIO (R2 stand-in), Mailpit
pnpm run dev          # web + api (+ runner when it exists)
```

Copy `apps/api/.env.example` → `apps/api/.env` on first run. Web: http://localhost:3100 · API: http://localhost:8100/docs. If ports are busy, run `pnpm run dev:free-ports`.
