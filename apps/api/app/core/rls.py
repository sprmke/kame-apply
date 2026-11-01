"""Row-level security helpers shared by migrations and the request layer.

Session variables (set per transaction, never per connection):
  app.user_id       the authenticated user
  app.workspace_id  the active workspace (set only after membership is verified)

`current_setting(name, true)` returns NULL when unset but '' after a transaction-local value has
been reset, so every policy goes through NULLIF(..., '') to fail closed in both cases.
"""

from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

APP_ROLE = "kame_apply_app"

WORKSPACE_EXPR = "NULLIF(current_setting('app.workspace_id', true), '')::uuid"
USER_EXPR = "NULLIF(current_setting('app.user_id', true), '')::uuid"


def tenant_rls_sql(table: str, *, allow_null_workspace_insert: bool = False) -> list[str]:
    """SQL enabling and forcing RLS on a table that has a `workspace_id` column.

    Rows are visible and writable only when `workspace_id` equals the active workspace. With
    `allow_null_workspace_insert`, system rows (workspace_id NULL) may be inserted but never read
    by tenants (used by activity_log for platform events).
    """
    check = f"workspace_id = {WORKSPACE_EXPR}"
    if allow_null_workspace_insert:
        check = f"workspace_id IS NULL OR {check}"
    return [
        f"ALTER TABLE {table} ENABLE ROW LEVEL SECURITY",
        f"ALTER TABLE {table} FORCE ROW LEVEL SECURITY",
        f"DROP POLICY IF EXISTS tenant_isolation ON {table}",
        f"CREATE POLICY tenant_isolation ON {table} "
        f"USING (workspace_id = {WORKSPACE_EXPR}) WITH CHECK ({check})",
    ]


async def set_request_context(
    session: AsyncSession, *, user_id: str | None, workspace_id: str | None = None
) -> None:
    """Set the transaction-local RLS variables. `set_config(..., true)` == SET LOCAL."""
    await session.execute(
        text(
            "SELECT set_config('app.user_id', :uid, true), set_config('app.workspace_id', :wid, true)"
        ),
        {"uid": user_id or "", "wid": workspace_id or ""},
    )
