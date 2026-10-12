from contextlib import asynccontextmanager

from fastapi import FastAPI

from app import models  # noqa: F401  (imported so its tables are registered on Base)
from app.config import settings
from app.database import Base, engine
from app.routers import auth, health


@asynccontextmanager
async def lifespan(app: FastAPI):
    # Runs once at startup: create any tables that don't exist yet.
    # (Fine for learning; a real project would use Alembic migrations.)
    Base.metadata.create_all(bind=engine)
    yield


app = FastAPI(
    title=settings.app_name,
    description="A mini banking API: accounts, deposits, withdrawals and transfers.",
    version="0.1.0",
    lifespan=lifespan,
)

app.include_router(health.router)
app.include_router(auth.router)
