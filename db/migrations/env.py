"""Alembic environment.

Resolves the engine from `db.session` so we share the FK/WAL pragmas with the
runtime app. Migrations run online (against a real connection) only — offline
SQL generation isn't wired up because this is a local-first app, not a CI
deploy target.
"""

from __future__ import annotations

from logging.config import fileConfig

from alembic import context
from sqlalchemy import engine_from_config, pool

from db.models import Base

config = context.config

if config.config_file_name is not None:
    fileConfig(config.config_file_name)

target_metadata = Base.metadata


def run_migrations_online() -> None:
    """Respect whichever URL the caller has configured.

    The default comes from `alembic.ini`. Tests and the app-startup auto-migrate
    hook override `sqlalchemy.url` programmatically via `Config.set_main_option`.
    """
    connectable = engine_from_config(
        config.get_section(config.config_ini_section, {}),
        prefix="sqlalchemy.",
        poolclass=pool.NullPool,
    )

    with connectable.connect() as connection:
        context.configure(
            connection=connection,
            target_metadata=target_metadata,
            render_as_batch=True,  # SQLite-friendly: emit batch-mode ALTERs for future revs
        )
        with context.begin_transaction():
            context.run_migrations()


if context.is_offline_mode():
    raise RuntimeError("Offline mode is not supported for this project")

run_migrations_online()
