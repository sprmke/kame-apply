# Spike 2: Oracle Always Free A1

**Date:** 2026-11-02 · **Decision: Keep (primary target) · Fallback: Hetzner CAX11**

## Decision

**Keep Oracle Always Free Ampere A1** as the primary production host target. **Hetzner CAX11** (or CX22) remains the paid fallback with the same Compose file (`infra/docker-compose.prod.yml`). Live A1 provisioning stays an **operator step** (needs the owner's Oracle Cloud tenancy and a region with capacity); engineering does not block on it.

## Evidence recorded without a live A1

1. **Allowance (public / reported):** Always Free A1 reported as **2 OCPU / 12 GB** since June 2026 (down from 4/24). Phase 14 Compose is sized for that envelope (Postgres + API + DBOS workers + one Chromium).
2. **aarch64 dependency pre-check (2026-10-28):** `linux/aarch64` wheels exist for `typst` 0.15.0, `onnxruntime` 1.31.1, `playwright` 1.64.1, `numpy` 2.5.4, `asyncpg` 0.32.0, `pydantic-core` 2.50.1 (cp313 manylinux aarch64); `pgvector/pgvector:pg17` is multi-arch. Dependency risk for ARM is low.
3. **Related spikes:** CDP screencast proven on localhost (28 fps); fastembed ~51 texts/s on laptop (plan 3–5× slower on A1). Re-time on the VM after first bring-up.
4. **Prod path shipped:** Phase 14 host harden, Compose, Caddy, backups, and deploy scripts already target this layout. First bring-up uses `applywave` (see `docs/architecture/deployment.md`).

## Operator checklist (first A1)

1. Provision A1 Flex in a region with capacity; confirm console allowance (OCPU / GB).
2. Run `infra/host/harden.sh`; deploy with `APPLYWAVE=applywave pnpm run deploy:api:prod` (and migrate / web).
3. `docker stats` peak memory with Postgres + API + one Chromium; record headroom in this note.
4. Re-run fastembed / RenderCV / CDP on the VM; append numbers here.
5. If capacity or memory fails: switch DNS to Hetzner CAX11, same Compose; mark host change in deployment.md.

## Pass / fail

| Criterion | Result |
| --- | --- |
| Prefer Oracle A1 for $0 host | **Keep** |
| Compose + ARM deps viable | **Pass** (pre-check) |
| Live memory measured on A1 | **Deferred** (operator + account) |
| Fallback documented | **Hetzner CAX11** |
