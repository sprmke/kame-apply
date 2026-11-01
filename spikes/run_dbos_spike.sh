#!/usr/bin/env bash
set -euo pipefail
cd "$(dirname "$0")/.."
export SPIKE_OUT="$(mktemp -d)"
PY=.venv/bin/python
docker compose -f infra/docker-compose.dev.yml exec -T postgres psql -U kame_apply -d postgres -q -c "DROP DATABASE IF EXISTS kame_apply_spike WITH (FORCE)" -c "CREATE DATABASE kame_apply_spike OWNER kame_apply"
echo "== durability: start, wait for recv, SIGKILL, restart, send =="
$PY spikes/dbos_spike.py start & PID=$!
sleep 6; kill -9 $PID; wait $PID 2>/dev/null || true
echo "killed; step1 runs so far: $(wc -l < $SPIKE_OUT/step1.log)"
$PY spikes/dbos_spike.py resume
echo "== queues =="; $PY spikes/dbos_spike.py queues
echo "== cron =="; $PY spikes/dbos_spike.py cron
