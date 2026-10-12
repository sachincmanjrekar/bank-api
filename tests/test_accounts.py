import pytest

from conftest import balance

# ---------- accounts ----------


def test_create_account_starts_at_zero(client, alice):
    response = client.post("/accounts", headers=alice)
    assert response.status_code == 201
    body = response.json()
    assert body["balance"] == "0.00"
    assert len(body["account_number"]) == 12
    assert body["account_number"].isdigit()


def test_list_shows_only_my_accounts(client, alice, bob, alice_account, bob_account):
    accounts = client.get("/accounts", headers=alice).json()
    assert [a["id"] for a in accounts] == [alice_account["id"]]


def test_cannot_see_someone_elses_account(client, bob, alice_account):
    response = client.get(f"/accounts/{alice_account['id']}", headers=bob)
    assert response.status_code == 404


def test_accounts_require_login(client):
    assert client.post("/accounts").status_code == 401
    assert client.get("/accounts").status_code == 401


# ---------- deposit / withdraw ----------


def test_deposit_increases_balance(client, alice, alice_account):
    response = client.post(
        f"/accounts/{alice_account['id']}/deposit",
        headers=alice,
        json={"amount": "50.25", "description": "salary"},
    )
    assert response.status_code == 201
    assert response.json()["type"] == "deposit"
    assert response.json()["balance_after"] == "150.25"
    assert balance(client, alice, alice_account) == "150.25"


def test_withdraw_decreases_balance(client, alice, alice_account):
    response = client.post(
        f"/accounts/{alice_account['id']}/withdraw", headers=alice, json={"amount": "40.00"}
    )
    assert response.status_code == 201
    assert response.json()["balance_after"] == "60.00"


def test_withdraw_more_than_balance_is_refused(client, alice, alice_account):
    response = client.post(
        f"/accounts/{alice_account['id']}/withdraw", headers=alice, json={"amount": "100.01"}
    )
    assert response.status_code == 400
    assert response.json()["detail"] == "Insufficient funds"
    assert balance(client, alice, alice_account) == "100.00"  # unchanged


# One test function, run once per bad value.
@pytest.mark.parametrize("amount", ["0", "-5", "1.999", "abc"])
def test_invalid_amounts_are_rejected(client, alice, alice_account, amount):
    response = client.post(
        f"/accounts/{alice_account['id']}/deposit", headers=alice, json={"amount": amount}
    )
    assert response.status_code == 422
    assert balance(client, alice, alice_account) == "100.00"


def test_decimal_money_has_no_float_drift(client, alice, alice_account):
    for _ in range(3):
        client.post(
            f"/accounts/{alice_account['id']}/deposit", headers=alice, json={"amount": "0.10"}
        )
    # With floats, 0.1 + 0.1 + 0.1 == 0.30000000000000004
    assert balance(client, alice, alice_account) == "100.30"


def test_cannot_deposit_into_someone_elses_account(client, bob, alice_account):
    response = client.post(
        f"/accounts/{alice_account['id']}/deposit", headers=bob, json={"amount": "5.00"}
    )
    assert response.status_code == 404


# ---------- statement ----------


def make_deposits(client, headers, account, count):
    for i in range(count):
        client.post(
            f"/accounts/{account['id']}/deposit", headers=headers, json={"amount": f"{i + 1}.00"}
        )


def test_statement_is_newest_first(client, alice, alice_account):
    client.post(f"/accounts/{alice_account['id']}/withdraw", headers=alice, json={"amount": "1.00"})
    rows = client.get(f"/accounts/{alice_account['id']}/transactions", headers=alice).json()
    assert [r["type"] for r in rows] == ["withdrawal", "deposit"]


def test_statement_pages_have_no_gaps_or_repeats(client, alice, alice_account):
    make_deposits(client, alice, alice_account, 6)  # 7 rows in total with the fixture's deposit
    url = f"/accounts/{alice_account['id']}/transactions"
    page1 = client.get(url, headers=alice, params={"limit": 3, "offset": 0}).json()
    page2 = client.get(url, headers=alice, params={"limit": 3, "offset": 3}).json()
    page3 = client.get(url, headers=alice, params={"limit": 3, "offset": 6}).json()
    ids = [r["id"] for r in page1 + page2 + page3]
    assert len(page1) == 3 and len(page2) == 3 and len(page3) == 1
    assert len(set(ids)) == 7
    assert ids == sorted(ids, reverse=True)


def test_statement_filter_by_type(client, alice, alice_account):
    client.post(f"/accounts/{alice_account['id']}/withdraw", headers=alice, json={"amount": "1.00"})
    rows = client.get(
        f"/accounts/{alice_account['id']}/transactions",
        headers=alice,
        params={"type": "withdrawal"},
    ).json()
    assert [r["type"] for r in rows] == ["withdrawal"]


@pytest.mark.parametrize("params", [{"limit": 0}, {"limit": 101}, {"offset": -1}, {"type": "x"}])
def test_statement_rejects_bad_query_params(client, alice, alice_account, params):
    response = client.get(
        f"/accounts/{alice_account['id']}/transactions", headers=alice, params=params
    )
    assert response.status_code == 422


def test_cannot_read_someone_elses_statement(client, bob, alice_account):
    response = client.get(f"/accounts/{alice_account['id']}/transactions", headers=bob)
    assert response.status_code == 404
