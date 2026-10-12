import random
import time
from collections.abc import Callable, Generator

from fastapi import HTTPException, status
from sqlalchemy import create_engine, event
from sqlalchemy.exc import OperationalError
from sqlalchemy.orm import DeclarativeBase, Session, sessionmaker

from app.config import settings

# SQLite only allows the thread that opened a connection to use it;
# FastAPI serves requests from several threads, so we relax that check.
# PostgreSQL doesn't need this.
connect_args = {"check_same_thread": False} if settings.database_url.startswith("sqlite") else {}

# pool_pre_ping: test a pooled connection before using it, and replace it if the
# server closed it (Aurora DSQL closes connections after 1 hour).
engine_options = {"connect_args": connect_args, "pool_pre_ping": True}
if settings.database_iam_auth:
    # On first connect SQLAlchemy looks for PostgreSQL's hstore extension inside a
    # SAVEPOINT; Aurora DSQL supports neither, so skip that lookup.
    engine_options["use_native_hstore"] = False

engine = create_engine(settings.database_url, **engine_options)
SessionLocal = sessionmaker(bind=engine, autoflush=False)

if settings.database_iam_auth:
    import boto3  # only needed for DSQL; on Lambda it's provided by the runtime

    dsql = boto3.client("dsql")

    @event.listens_for(engine, "do_connect")
    def use_iam_token(dialect, conn_rec, cargs, cparams):
        # The token works like a password but expires after 15 minutes; it's only
        # checked when a connection opens, so open connections keep working.
        cparams["password"] = dsql.generate_db_connect_admin_auth_token(
            Hostname=cparams["host"], Region=dsql.meta.region_name
        )


class Base(DeclarativeBase):
    """Parent class for all database tables (models)."""


def get_db() -> Generator[Session]:
    """FastAPI dependency: opens a DB session per request and always closes it."""
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


SERIALIZATION_FAILURE = "40001"  # PostgreSQL error code; DSQL uses it for write conflicts


def commit_with_retry[T](db: Session, work: Callable[[], T], attempts: int = 3) -> T:
    """Run `work` (which changes data), commit, and retry if the database reports a conflict.

    Aurora DSQL uses optimistic concurrency: two transactions that touch the same
    row both run, and the second to commit fails with a serialization error instead
    of waiting for a lock. Re-running the whole unit of work (re-reading the
    balance) is the standard fix. HTTPExceptions raised by `work` (e.g. insufficient
    funds) are not retried.
    """
    for attempt in range(1, attempts + 1):
        try:
            result = work()
            db.commit()
            return result
        except OperationalError as exc:
            db.rollback()
            if getattr(exc.orig, "sqlstate", None) != SERIALIZATION_FAILURE:
                raise
            if attempt == attempts:
                raise HTTPException(
                    status.HTTP_409_CONFLICT, "Account is busy, please retry"
                ) from exc
            time.sleep(random.uniform(0, 0.05 * 2**attempt))  # back off, with jitter
    raise AssertionError("unreachable")
