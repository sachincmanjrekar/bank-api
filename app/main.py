from fastapi import FastAPI

from app.config import settings
from app.routers import accounts, auth, health, transfers

# Tables are created and changed by Alembic migrations, not by the app:
#   alembic upgrade head

app = FastAPI(
    title=settings.app_name,
    description="A mini banking API: accounts, deposits, withdrawals and transfers.",
    version="0.1.0",
)

app.include_router(health.router)
app.include_router(auth.router)
app.include_router(accounts.router)
app.include_router(transfers.router)
