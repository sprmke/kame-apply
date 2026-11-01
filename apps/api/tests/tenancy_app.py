"""A test-only app exposing probe routes wired exactly like real tenant routes will be."""

import uuid
from collections.abc import AsyncIterator
from contextlib import asynccontextmanager

from fastapi import APIRouter, Depends, Header, Request
from sqlalchemy import text

from app.audit import service as audit
from app.core.config import Settings
from app.core.errors import AppError
from app.core.security import WorkspaceContext, current_user_id, require_action
from app.main import create_app
from tests.conftest import TEST_DB_URL

probe = APIRouter(prefix="/api/v1/probe")


@probe.get("")
async def list_probe(ctx: WorkspaceContext = Depends(require_action("data.read"))):
    rows = (await ctx.session.execute(text("SELECT label FROM rls_probe ORDER BY label"))).all()
    return {"labels": [r[0] for r in rows], "role": ctx.role}


@probe.post("")
async def write_probe(label: str, ctx: WorkspaceContext = Depends(require_action("data.write"))):
    await ctx.session.execute(
        text("INSERT INTO rls_probe (workspace_id, label) VALUES (:w, :l)"),
        {"w": ctx.workspace_id, "l": label},
    )
    await audit.record(ctx, action="probe.created", target_type="probe", target_id=label)
    return {"ok": True}


@probe.delete("/workspace")
async def delete_workspace(ctx: WorkspaceContext = Depends(require_action("workspace.delete"))):
    return {"ok": True}


@probe.get("/audit")
async def read_audit(ctx: WorkspaceContext = Depends(require_action("activity.read"))):
    rows = (await ctx.session.execute(text("SELECT action, actor_id FROM activity_log"))).all()
    return {"events": [{"action": r[0], "actor_id": r[1]} for r in rows]}


@probe.post("/boom")
async def boom(ctx: WorkspaceContext = Depends(require_action("data.write"))):
    await ctx.session.execute(
        text("INSERT INTO rls_probe (workspace_id, label) VALUES (:w, 'should-roll-back')"),
        {"w": ctx.workspace_id},
    )
    raise AppError("boom", "forced failure after a write", 500)


def build_test_app():
    app = create_app(Settings(database_url=TEST_DB_URL, environment="test", log_json=False))

    async def fake_user(
        request: Request, x_test_user: str | None = Header(default=None)
    ) -> uuid.UUID:
        if not x_test_user:
            raise AppError("unauthenticated", "Authentication required", 401)
        return uuid.UUID(x_test_user)

    app.dependency_overrides[current_user_id] = fake_user
    app.include_router(probe)
    return app


@asynccontextmanager
async def running(app) -> AsyncIterator[None]:
    async with app.router.lifespan_context(app):
        yield
