"""Alembic environment.

Initial institutional baseline for decision risk infrastructure.
"""

from __future__ import annotations

import os
import sys
from logging.config import fileConfig

from alembic import context
from sqlalchemy import engine_from_config, pool


# Ensure `backend/` is on sys.path so `import app...` works when running Alembic.
BASE_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
if BASE_DIR not in sys.path:
    sys.path.insert(0, BASE_DIR)

from app.core.base import Base  # noqa: E402
from app.core.env import load_env_if_present  # noqa: E402


def _import_models() -> None:
    # Import all models so Base.metadata is fully populated.
    from app.models import (  # noqa: F401
        consensus_pressure,
        decision_context,
        decision_environment_snapshot,
        decision_impact_record,
        decision_risk_event,
        information_event,
        narrative_cluster,
        re_evaluation_log,
        timing_distortion,
    )


_import_models()

config = context.config

if config.config_file_name is not None:
    fileConfig(config.config_file_name)

target_metadata = Base.metadata


def get_database_url() -> str:
    load_env_if_present()
    url = os.environ.get("DATABASE_URL")
    if not url:
        raise RuntimeError(
            "Missing required env var DATABASE_URL for Alembic migrations. "
            "Example: postgresql+psycopg://user:pass@host:5432/coin87"
        )
    return url


def run_migrations_offline() -> None:
    """Run migrations in 'offline' mode."""
    url = get_database_url()
    context.configure(
        url=url,
        target_metadata=target_metadata,
        literal_binds=True,
        dialect_opts={"paramstyle": "named"},
        compare_type=True,
        compare_server_default=True,
    )

    with context.begin_transaction():
        context.run_migrations()


def run_migrations_online() -> None:
    """Run migrations in 'online' mode."""
    configuration = config.get_section(config.config_ini_section) or {}
    configuration["sqlalchemy.url"] = get_database_url()

    connectable = engine_from_config(
        configuration,
        prefix="sqlalchemy.",
        poolclass=pool.NullPool,
        future=True,
    )

    with connectable.connect() as connection:
        context.configure(
            connection=connection,
            target_metadata=target_metadata,
            compare_type=True,
            compare_server_default=True,
        )

        with context.begin_transaction():
            context.run_migrations()


if context.is_offline_mode():
    run_migrations_offline()
else:
    run_migrations_online()

