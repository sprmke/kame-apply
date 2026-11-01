"""Durable apply_run workflow (DBOS when configured; otherwise inline helpers)."""

from __future__ import annotations

import logging
import os
from typing import Any

log = logging.getLogger(__name__)

_DBOS_READY = False


def ensure_dbos() -> bool:
    global _DBOS_READY
    if _DBOS_READY:
        return True
    url = os.environ.get("DBOS_SYSTEM_DATABASE_URL")
    if not url:
        return False
    try:
        from dbos import DBOS, DBOSConfig

        config: DBOSConfig = {"name": "kame-apply", "system_database_url": url}
        DBOS(config=config)
        DBOS.launch()
        try:
            DBOS.register_queue(
                "apply_runs",
                global_concurrency=2,
                partition_concurrency=1,
            )
        except Exception:  # noqa: S110 — queue may already exist
            pass
        _DBOS_READY = True
        return True
    except Exception:
        log.exception("dbos_launch_failed")
        return False


def send_checkpoint_decision(checkpoint_id: str, decision: str) -> None:
    if not ensure_dbos():
        return
    from dbos import DBOS

    DBOS.send(f"checkpoint:{checkpoint_id}", {"decision": decision})


def start_apply_workflow(workspace_id: str, run_id: str) -> str | None:
    """Enqueue durable orchestration. Returns workflow id or None (runner pulls queue)."""
    if not ensure_dbos():
        return None
    from dbos import DBOS, SetWorkflowID

    @DBOS.workflow()
    def apply_run_workflow(ws: str, rid: str) -> dict[str, Any]:
        # Orchestration only: runner process drives browser steps; this workflow
        # waits on final_review / completion signals via recv topics.
        DBOS.logger.info("apply_run start ws=%s run=%s", ws, rid)
        # Wait up to 24h for completion signal from runner via API send.
        result = DBOS.recv(f"apply_run:{rid}:done", timeout_seconds=86400)
        return result or {"status": "timeout"}

    wf_id = f"apply-run-{run_id}"
    with SetWorkflowID(wf_id):
        DBOS.start_workflow(apply_run_workflow, workspace_id, run_id)
    return wf_id


def signal_run_done(run_id: str, payload: dict[str, Any]) -> None:
    if not ensure_dbos():
        return
    from dbos import DBOS

    DBOS.send(f"apply_run:{run_id}:done", payload)
