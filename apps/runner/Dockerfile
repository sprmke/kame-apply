# Production cloud runner image (Phase 15). Build from the monorepo root.
FROM python:3.13-slim-bookworm AS base
ENV PYTHONDONTWRITEBYTECODE=1 PYTHONUNBUFFERED=1
RUN apt-get update && apt-get install -y --no-install-recommends curl ca-certificates \
  && rm -rf /var/lib/apt/lists/*
WORKDIR /app

COPY --from=ghcr.io/astral-sh/uv:0.9 /uv /usr/local/bin/uv
COPY pyproject.toml uv.lock ./
COPY apps/api/pyproject.toml apps/api/
COPY packages/py-core/pyproject.toml packages/py-core/
COPY apps/runner/pyproject.toml apps/runner/
RUN uv sync --frozen --no-dev --package kame-apply-runner || uv sync --no-dev --package kame-apply-runner

COPY apps/runner apps/runner
COPY packages/py-core packages/py-core
WORKDIR /app/apps/runner
RUN uv run playwright install --with-deps chromium

ENV KAME_RUNNER_MODE=cloud \
    KAME_RUNNER_HEADED=false
CMD ["uv", "run", "kame-runner"]
