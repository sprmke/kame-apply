import asyncio
import os

from alembic import context
from sqlalchemy import pool
from sqlalchemy.engine import Connection
from sqlalchemy.ext.asyncio import create_async_engine

from app.agent_bridge import models as _agent_bridge_models  # noqa: F401
from app.answers import models as _answer_desk_models  # noqa: F401
from app.applications import models as _application_models  # noqa: F401
from app.audit import models as _audit_models  # noqa: F401  (register tables)
from app.auth import models as _auth_models  # noqa: F401
from app.autosubmit import models as _autosubmit_models  # noqa: F401
from app.companies import models as _company_models  # noqa: F401
from app.core.config import get_settings
from app.core.db import Base
from app.extension import models as _extension_models  # noqa: F401
from app.gaps import models as _gaps_models  # noqa: F401
from app.ingest import models as _ingest_models  # noqa: F401
from app.interview import models as _interview_models  # noqa: F401
from app.jobs import models as _job_models  # noqa: F401
from app.matching import models as _matching_models  # noqa: F401
from app.notifications import models as _notification_models  # noqa: F401
from app.profiles import models as _profile_models  # noqa: F401
from app.referrals import models as _referrals_models  # noqa: F401
from app.responses import models as _responses_models  # noqa: F401
from app.resumes import models as _resume_models  # noqa: F401
from app.safety import models as _safety_models  # noqa: F401
from app.schedules import models as _schedule_models  # noqa: F401
from app.sources import models as _source_models  # noqa: F401
from app.taxonomy import models as _taxonomy_models  # noqa: F401
from app.tracks import models as _track_models  # noqa: F401
from app.workspaces import models as _ws_models  # noqa: F401

config = context.config
target_metadata = Base.metadata


def _url() -> str:
    # Migrations run as the owner role, never as the RLS-restricted app role.
    return os.environ.get("MIGRATION_DATABASE_URL") or get_settings().migration_database_url


def run_migrations_offline() -> None:
    context.configure(url=_url(), target_metadata=target_metadata, literal_binds=True)
    with context.begin_transaction():
        context.run_migrations()


def _do_run(connection: Connection) -> None:
    context.configure(connection=connection, target_metadata=target_metadata, compare_type=True)
    with context.begin_transaction():
        context.run_migrations()


async def run_migrations_online() -> None:
    engine = create_async_engine(_url(), poolclass=pool.NullPool)
    async with engine.connect() as connection:
        await connection.run_sync(_do_run)
    await engine.dispose()


if context.is_offline_mode():
    run_migrations_offline()
else:
    asyncio.run(run_migrations_online())
