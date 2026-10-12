"""Retry on optimistic-concurrency conflicts (Aurora DSQL), simulated locally.

SQLite and our local PostgreSQL never raise these errors for our endpoints, so we
fake one: Session.commit raises a serialization failure the first N times.
"""

import pytest
from conftest import balance
from sqlalchemy.exc import OperationalError
from sqlalchemy.orm import Session


class FakeSerializationFailure(Exception):
    sqlstate = "40001"  # what psycopg reports for a PostgreSQL/DSQL write conflict


class FakeOtherError(Exception):
    sqlstate = "08006"  # connection failure: must NOT be retried


@pytest.fixture
def failing_commits(monkeypatch):
    """Make the next `count` commits fail with `error`, then behave normally."""
    real_commit = Session.commit
    state = {"left": 0, "error": FakeSerializationFailure, "calls": 0}

    def commit(self):
        state["calls"] += 1
        if state["left"] > 0:
            state["left"] -= 1
            raise OperationalError("COMMIT", {}, state["error"]())
        return real_commit(self)

    monkeypatch.setattr(Session, "commit", commit)

    def arm(count, error=FakeSerializationFailure):
        state.update(left=count, error=error, calls=0)
        return state

    return arm


def deposit(client, headers, account, amount="10.00"):
    return client.post(
        f"/accounts/{account['id']}/deposit", headers=headers, json={"amount": amount}
    )


def test_conflict_is_retried_and_applied_once(client, alice, alice_account, failing_commits):
    state = failing_commits(2)  # first two commits conflict, third succeeds
    response = deposit(client, alice, alice_account)
    assert response.status_code == 201
    assert state["calls"] == 3
    assert balance(client, alice, alice_account) == "110.00"  # applied once, not three times
    rows = client.get(f"/accounts/{alice_account['id']}/transactions", headers=alice).json()
    assert len(rows) == 2  # fixture's deposit + this one


def test_persistent_conflict_returns_409_and_changes_nothing(
    client, alice, alice_account, failing_commits
):
    failing_commits(3)  # every attempt conflicts
    response = deposit(client, alice, alice_account)
    assert response.status_code == 409
    assert balance(client, alice, alice_account) == "100.00"


def test_transfer_is_retried_too(client, alice, bob, alice_account, bob_account, failing_commits):
    failing_commits(1)
    response = client.post(
        "/transfers",
        headers=alice,
        json={
            "from_account_id": alice_account["id"],
            "to_account_number": bob_account["account_number"],
            "amount": "30.00",
        },
    )
    assert response.status_code == 201
    assert balance(client, alice, alice_account) == "70.00"
    assert balance(client, bob, bob_account) == "30.00"


def test_other_database_errors_are_not_retried(client, alice, alice_account, failing_commits):
    state = failing_commits(1, error=FakeOtherError)
    with pytest.raises(OperationalError):
        deposit(client, alice, alice_account)
    assert state["calls"] == 1
