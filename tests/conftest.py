import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from app.database import Base, get_db
from app.main import app

# In-memory SQLite: lives in RAM, never touches bank.db, leaves no file behind.
# StaticPool makes every connection share that one in-memory database.
engine = create_engine(
    "sqlite://", connect_args={"check_same_thread": False}, poolclass=StaticPool
)
TestingSessionLocal = sessionmaker(bind=engine, autoflush=False)


def override_get_db():
    db = TestingSessionLocal()
    try:
        yield db
    finally:
        db.close()


@pytest.fixture
def client():
    """A test client with a fresh, empty database for every single test."""
    Base.metadata.create_all(bind=engine)
    app.dependency_overrides[get_db] = override_get_db
    yield TestClient(app)
    app.dependency_overrides.clear()
    Base.metadata.drop_all(bind=engine)


def register_and_login(client: TestClient, email: str) -> dict:
    """Creates a real user through the API and returns their Authorization header."""
    client.post(
        "/auth/register",
        json={"email": email, "full_name": "Test User", "password": "password123"},
    )
    response = client.post("/auth/login", data={"username": email, "password": "password123"})
    return {"Authorization": f"Bearer {response.json()['access_token']}"}


@pytest.fixture
def alice(client):
    return register_and_login(client, "alice@example.com")


@pytest.fixture
def bob(client):
    return register_and_login(client, "bob@example.com")


@pytest.fixture
def alice_account(client, alice):
    """Alice's account with 100.00 already deposited."""
    account = client.post("/accounts", headers=alice).json()
    client.post(f"/accounts/{account['id']}/deposit", headers=alice, json={"amount": "100.00"})
    return account


@pytest.fixture
def bob_account(client, bob):
    """Bob's empty account."""
    return client.post("/accounts", headers=bob).json()


def balance(client: TestClient, headers: dict, account: dict) -> str:
    return client.get(f"/accounts/{account['id']}", headers=headers).json()["balance"]
