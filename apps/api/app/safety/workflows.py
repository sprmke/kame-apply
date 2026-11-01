"""DBOS wrappers for assess_job_risk."""

from __future__ import annotations

import asyncio
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

        config: DBOSConfig = {
            "name": "kame-apply",
            "system_database_url": url,
        }
        DBOS(config=config)
        DBOS.launch()
        _DBOS_READY = True
        return True
    except Exception:
        return False


def enqueue_assess_job_risk(workspace_id: str, job_id: str) -> None:
    if not ensure_dbos():
        return
    from dbos import DBOS, SetWorkflowID

    @DBOS.workflow()
    def assess_job_risk_workflow(ws: str, jid: str) -> str:
        DBOS.logger.info("assess_job_risk ws=%s job=%s", ws, jid)
        asyncio.get_event_loop()
        # Durable entry: actual work runs via API service when invoked with a session.
        return jid

    with SetWorkflowID(f"assess-job-risk-{job_id}"):
        DBOS.start_workflow(assess_job_risk_workflow, workspace_id, job_id)


async def assess_job_risk_inline(ctx, job_id: uuid.UUID, *, cheap: bool = True):
    """Called from discovery / scoring paths without requiring DBOS."""
    from app.safety import service

    return await service.assess_and_store(ctx, job_id, run_network=not cheap, run_llm=False)
