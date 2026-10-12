from logging.config import fileConfig

from alembic import context
from app import models  # noqa: F401  (imported so its tables are registered on Base)
from app.config import settings
from app.database import Base, engine

# this is the Alembic Config object, which provides
# access to the values within the .ini file in use.
config = context.config

# Use the same database URL as the app (from config.py / env vars), so it is
# defined in one place only, and on AWS we just set DATABASE_URL.
config.set_main_option("sqlalchemy.url", settings.database_url)

# Interpret the config file for Python logging.
# This line sets up loggers basically.
if config.config_file_name is not None:
    fileConfig(config.config_file_name)

# Our models' tables: autogenerate compares these against the real database.
target_metadata = Base.metadata

# SQLite can't ALTER most things in place; "batch mode" makes Alembic copy the
# table instead. PostgreSQL doesn't need it.
render_as_batch = settings.database_url.startswith("sqlite")

# other values from the config, defined by the needs of env.py,
# can be acquired:
# my_important_option = config.get_main_option("my_important_option")
# ... etc.


def run_migrations_offline() -> None:
    """Run migrations in 'offline' mode.

    This configures the context with just a URL
    and not an Engine, though an Engine is acceptable
    here as well.  By skipping the Engine creation
    we don't even need a DBAPI to be available.

    Calls to context.execute() here emit the given string to the
    script output.

    """
    url = config.get_main_option("sqlalchemy.url")
    context.configure(
        url=url,
        target_metadata=target_metadata,
        literal_binds=True,
        dialect_opts={"paramstyle": "named"},
        render_as_batch=render_as_batch,
    )

    with context.begin_transaction():
        context.run_migrations()


def run_migrations_online() -> None:
    """Run migrations in 'online' mode.

    In this scenario we need to create an Engine
    and associate a connection with the context.

    """
    # Reuse the app's engine so migrations connect exactly like the app does,
    # including the IAM auth token for Aurora DSQL.
    with engine.connect() as connection:
        context.configure(
            connection=connection,
            target_metadata=target_metadata,
            render_as_batch=render_as_batch,
        )

        with context.begin_transaction():
            context.run_migrations()


if context.is_offline_mode():
    run_migrations_offline()
else:
    run_migrations_online()
