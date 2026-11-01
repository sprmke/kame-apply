"""Agent task inbox: queue work for the user's own Claude."""

from __future__ import annotations

import uuid
from datetime import UTC, datetime, timedelta
from typing import Any

from sqlalchemy import select, text, update

from app.agent_bridge.models import AgentTask, AiFeatureRouting
from app.audit import service as audit
from app.core.errors import AppError
from app.core.security import WorkspaceContext

LEASE_TTL = timedelta(minutes=15)
FEATURES = (
    "tailoring",
    "answer_drafting",
    "market_research",
    "deep_fit_review",
    "interview_prep",
)


async def get_routing(ctx: WorkspaceContext) -> list[dict[str, Any]]:
    rows = (
        (
            await ctx.session.execute(
                select(AiFeatureRouting).where(AiFeatureRouting.workspace_id == ctx.workspace_id)
            )
        )
        .scalars()
        .all()
    )
    by_feature = {r.feature: r for r in rows}
    out = []
    for f in FEATURES:
        r = by_feature.get(f)
        out.append(
            {
                "feature": f,
                "route": r.route if r else "server",
                "fallback": r.fallback if r else False,
            }
        )
    return out


async def put_routing(
    ctx: WorkspaceContext, *, feature: str, route: str, fallback: bool
) -> dict[str, Any]:
    if feature not in FEATURES:
        raise AppError("validation_error", f"Unknown feature: {feature}", 400)
    if route not in ("server", "agent_inbox"):
        raise AppError("validation_error", "route must be server or agent_inbox", 400)
    row = (
        await ctx.session.execute(
            select(AiFeatureRouting).where(
                AiFeatureRouting.workspace_id == ctx.workspace_id,
                AiFeatureRouting.feature == feature,
            )
        )
    ).scalar_one_or_none()
    before = None
    if row is None:
        row = AiFeatureRouting(
            workspace_id=ctx.workspace_id, feature=feature, route=route, fallback=fallback
        )
        ctx.session.add(row)
    else:
        before = {"route": row.route, "fallback": row.fallback}
        row.route = route
        row.fallback = fallback
        row.updated_at = datetime.now(UTC)
    await ctx.session.flush()
    await audit.record(
        ctx,
        action="ai.feature_routing.updated",
        target_type="ai_feature_routing",
        target_id=str(row.id),
        before=before,
        after={"feature": feature, "route": route, "fallback": fallback},
    )
    return {"feature": feature, "route": route, "fallback": fallback}


async def create_task(
    ctx: WorkspaceContext,
    *,
    profile_id: uuid.UUID,
    kind: str,
    input_data: dict[str, Any],
    output_schema: dict[str, Any] | None = None,
    priority: int = 0,
    deadline_at: datetime | None = None,
    fallback_enabled: bool = False,
) -> AgentTask:
    task = AgentTask(
        workspace_id=ctx.workspace_id,
        profile_id=profile_id,
        kind=kind,
        input=input_data,
        output_schema=output_schema,
        status="queued",
        priority=priority,
        deadline_at=deadline_at,
        fallback_enabled=fallback_enabled,
        created_by=ctx.user_id,
    )
    ctx.session.add(task)
    await ctx.session.flush()
    await audit.record(
        ctx,
        action="agent_task.created",
        target_type="agent_task",
        target_id=str(task.id),
        after={"kind": kind, "profile_id": str(profile_id)},
        actor_type="user",
    )
    return task


async def inbox_status(ctx: WorkspaceContext) -> dict[str, Any]:
    now = datetime.now(UTC)
    # Requeue expired leases
    await ctx.session.execute(
        update(AgentTask)
        .where(
            AgentTask.workspace_id == ctx.workspace_id,
            AgentTask.status == "leased",
            AgentTask.lease_expires_at < now,
        )
        .values(status="queued", lease_expires_at=None, leased_by_client_id=None)
    )
    waiting = (
        (
            await ctx.session.execute(
                select(AgentTask).where(
                    AgentTask.workspace_id == ctx.workspace_id,
                    AgentTask.status.in_(("queued", "leased")),
                )
            )
        )
        .scalars()
        .all()
    )
    last_pickup = (
        await ctx.session.execute(
            text(
                "SELECT MAX(updated_at) FROM agent_tasks "
                "WHERE workspace_id = :wid AND status IN ('leased','done')"
            ),
            {"wid": ctx.workspace_id},
        )
    ).scalar_one_or_none()
    return {
        "waiting": len([t for t in waiting if t.status == "queued"]),
        "leased": len([t for t in waiting if t.status == "leased"]),
        "last_picked_up_at": last_pickup.isoformat() if last_pickup else None,
        "command": 'claude -p "/kame:work"',
    }


async def lease_next(
    ctx: WorkspaceContext,
    *,
    profile_id: uuid.UUID,
    client_id: str,
    kinds: list[str] | None = None,
) -> AgentTask | None:
    now = datetime.now(UTC)
    await ctx.session.execute(
        update(AgentTask)
        .where(
            AgentTask.workspace_id == ctx.workspace_id,
            AgentTask.status == "leased",
            AgentTask.lease_expires_at < now,
        )
        .values(status="queued", lease_expires_at=None, leased_by_client_id=None)
    )
    q = (
        select(AgentTask)
        .where(
            AgentTask.workspace_id == ctx.workspace_id,
            AgentTask.profile_id == profile_id,
            AgentTask.status == "queued",
        )
        .order_by(AgentTask.priority.desc(), AgentTask.created_at.asc())
        .limit(1)
        .with_for_update(skip_locked=True)
    )
    if kinds:
        q = q.where(AgentTask.kind.in_(kinds))
    task = (await ctx.session.execute(q)).scalar_one_or_none()
    if task is None:
        return None
    task.status = "leased"
    task.lease_expires_at = now + LEASE_TTL
    task.leased_by_client_id = client_id
    task.attempts = (task.attempts or 0) + 1
    task.updated_at = now
    await ctx.session.flush()
    await audit.record(
        ctx,
        action="agent_task.leased",
        target_type="agent_task",
        target_id=str(task.id),
        after={"client_id": client_id, "attempts": task.attempts},
        actor_type="agent",
    )
    return task


async def complete_task(
    ctx: WorkspaceContext,
    *,
    task_id: uuid.UUID,
    result: dict[str, Any],
    client_id: str,
) -> AgentTask:
    task = await ctx.session.get(AgentTask, task_id)
    if task is None or task.workspace_id != ctx.workspace_id:
        raise AppError("not_found", "Task not found", 404)
    if task.status == "done":
        return task  # idempotent
    if task.status not in ("leased", "queued"):
        raise AppError("conflict", f"Task status is {task.status}", 409)
    task.status = "done"
    task.result = result
    task.lease_expires_at = None
    task.updated_at = datetime.now(UTC)
    await ctx.session.flush()
    await audit.record(
        ctx,
        action="agent_task.completed",
        target_type="agent_task",
        target_id=str(task.id),
        after={"client_id": client_id, "kind": task.kind},
        actor_type="agent",
    )
    return task


async def fail_task(
    ctx: WorkspaceContext,
    *,
    task_id: uuid.UUID,
    error: str,
    client_id: str,
    requeue: bool = True,
) -> AgentTask:
    task = await ctx.session.get(AgentTask, task_id)
    if task is None or task.workspace_id != ctx.workspace_id:
        raise AppError("not_found", "Task not found", 404)
    if task.status == "done":
        return task
    now = datetime.now(UTC)
    if requeue and (task.attempts or 0) < 3:
        task.status = "queued"
        task.error = error
        task.lease_expires_at = None
        task.leased_by_client_id = None
    else:
        task.status = "failed"
        task.error = error
        task.lease_expires_at = None
    task.updated_at = now
    await ctx.session.flush()
    await audit.record(
        ctx,
        action="agent_task.failed",
        target_type="agent_task",
        target_id=str(task.id),
        after={"client_id": client_id, "error": error[:200], "status": task.status},
        actor_type="agent",
    )
    return task


def task_to_dict(task: AgentTask) -> dict[str, Any]:
    return {
        "id": str(task.id),
        "kind": task.kind,
        "input": task.input,
        "output_schema": task.output_schema,
        "status": task.status,
        "attempts": task.attempts,
        "lease_expires_at": task.lease_expires_at.isoformat() if task.lease_expires_at else None,
        "result": task.result,
        "error": task.error,
        "profile_id": str(task.profile_id),
    }
