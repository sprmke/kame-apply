# Production API image (Phase 14). Build from monorepo root.
FROM python:3.13-slim-bookworm AS base
ENV PYTHONDONTWRITEBYTECODE=1 PYTHONUNBUFFERED=1
RUN apt-get update && apt-get install -y --no-install-recommends curl \
  && rm -rf /var/lib/apt/lists/*
WORKDIR /app

COPY --from=ghcr.io/astral-sh/uv:0.9 /uv /usr/local/bin/uv
COPY pyproject.toml uv.lock ./
COPY apps/api/pyproject.toml apps/api/
COPY packages/py-core/pyproject.toml packages/py-core/
COPY apps/runner/pyproject.toml apps/runner/
RUN uv sync --frozen --no-dev --package kame-apply-api || uv sync --no-dev --package kame-apply-api

COPY apps/api apps/api
COPY packages/py-core packages/py-core
WORKDIR /app/apps/api
EXPOSE 8100
# forwarded-allow-ips is narrowed at runtime via TRUSTED_PROXIES / uvicorn flags in compose.
CMD ["uv", "run", "uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8100", "--proxy-headers", "--forwarded-allow-ips", "10.0.0.0/8,172.16.0.0/12,192.168.0.0/16"]
