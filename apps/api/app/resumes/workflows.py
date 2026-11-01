"""DBOS wrapper for tailor_application (optional durability)."""

from __future__ import annotations

import os
import uuid

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
        _DBOS_READY = True
        return True
    except Exception:
        return False


def enqueue_tailor(workspace_id: str, track_job_id: str) -> str | None:
    """Start durable tailor when DBOS is configured; else None (API runs inline)."""
    if not ensure_dbos():
        return None
    from dbos import DBOS, SetWorkflowID

    wid = f"tailor:{workspace_id}:{track_job_id}:{uuid.uuid4().hex[:8]}"

    @DBOS.workflow()
    def tailor_application_workflow(ws: str, tj: str) -> str:
        DBOS.logger.info("tailor_application ws=%s track_job=%s", ws, tj)
        # Heavy work stays in the HTTP service path for request-scoped DB;
        # this workflow records the enqueue for durability/observability.
        return tj

    with SetWorkflowID(wid):
        DBOS.start_workflow(tailor_application_workflow, workspace_id, track_job_id)
    return wid
