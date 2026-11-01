"""DBOS wrappers for discovery (service does the work; workflow adds durability)."""

from __future__ import annotations

import logging
import os

logger = logging.getLogger(__name__)

_DBOS_READY = False


def try_launch_dbos() -> bool:
    """Launch DBOS when system DB URL is configured. Safe no-op otherwise."""
    global _DBOS_READY
    if _DBOS_READY:
        return True
    url = os.environ.get("DBOS_SYSTEM_DATABASE_URL")
    if not url:
        return False
    try:
        from dbos import DBOS, DBOSConfig

        config: DBOSConfig = {
            "name": "kame-apply",
            "system_database_url": url,
        }
        DBOS(config=config)
        DBOS.launch()
        _DBOS_READY = True
        logger.info("dbos_launched")
        return True
    except Exception:
        logger.exception("dbos_launch_failed")
        return False


def enqueue_discover_track(workspace_id: str, track_id: str, run_id: str) -> None:
    """Best-effort durable enqueue; callers still may run inline."""
    if not try_launch_dbos():
        return
    from dbos import DBOS, SetWorkflowID

    @DBOS.workflow()
    def discover_track_workflow(ws: str, tid: str, rid: str) -> str:
        # Persistence happens via API service on resume paths; this records the intent.
        DBOS.logger.info("discover_track ws=%s track=%s run=%s", ws, tid, rid)
        return rid

    with SetWorkflowID(f"discover:{run_id}"):
        DBOS.start_workflow(discover_track_workflow, workspace_id, track_id, run_id)
