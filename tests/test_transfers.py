from decimal import Decimal

from conftest import balance


def transfer(client, headers, from_account, to_number, amount, **extra):
    return client.post(
        "/transfers",
        headers=headers,
        json={
            "from_account_id": from_account["id"],
            "to_account_number": to_number,
            "amount": amount,
            **extra,
        },
    )


def test_transfer_moves_money(client, alice, bob, alice_account, bob_account):
    response = transfer(
        client, alice, alice_account, bob_account["account_number"], "30.00", description="rent"
    )
    assert response.status_code == 201
    assert balance(client, alice, alice_account) == "70.00"
    assert balance(client, bob, bob_account) == "30.00"


def test_transfer_writes_both_sides_of_the_ledger(client, alice, bob, alice_account, bob_account):
    transfer(client, alice, alice_account, bob_account["account_number"], "30.00")

    alice_rows = client.get(f"/accounts/{alice_account['id']}/transactions", headers=alice).json()
    bob_rows = client.get(f"/accounts/{bob_account['id']}/transactions", headers=bob).json()

    assert alice_rows[0]["type"] == "transfer_out"
    assert alice_rows[0]["amount"] == "30.00"
    assert bob_rows[0]["type"] == "transfer_in"
    assert bob_rows[0]["amount"] == "30.00"
    assert bob_rows[0]["description"] == f"Transfer from {alice_account['account_number']}"


def test_response_does_not_leak_receivers_balance(client, alice, alice_account, bob_account):
    body = transfer(client, alice, alice_account, bob_account["account_number"], "30.00").json()
    assert body["account_id"] == alice_account["id"]
    assert body["balance_after"] == "70.00"  # Alice's balance, not Bob's


def test_insufficient_funds_changes_nothing(client, alice, bob, alice_account, bob_account):
    response = transfer(client, alice, alice_account, bob_account["account_number"], "500.00")
    assert response.status_code == 400
    assert balance(client, alice, alice_account) == "100.00"
    assert balance(client, bob, bob_account) == "0.00"
    bob_rows = client.get(f"/accounts/{bob_account['id']}/transactions", headers=bob).json()
    assert bob_rows == []


def test_cannot_transfer_to_same_account(client, alice, alice_account):
    response = transfer(client, alice, alice_account, alice_account["account_number"], "1.00")
    assert response.status_code == 400


def test_unknown_destination(client, alice, alice_account):
    response = transfer(client, alice, alice_account, "000000000000", "1.00")
    assert response.status_code == 404


def test_destination_must_be_12_digits(client, alice, alice_account):
    response = transfer(client, alice, alice_account, "abc", "1.00")
    assert response.status_code == 422


def test_cannot_send_from_someone_elses_account(client, bob, alice, alice_account, bob_account):
    response = transfer(client, bob, alice_account, bob_account["account_number"], "1.00")
    assert response.status_code == 404
    assert balance(client, alice, alice_account) == "100.00"


def test_total_money_is_conserved(client, alice, bob, alice_account, bob_account):
    transfer(client, alice, alice_account, bob_account["account_number"], "30.00")
    transfer(client, bob, bob_account, alice_account["account_number"], "12.34")
    transfer(client, alice, alice_account, bob_account["account_number"], "500.00")  # fails
    total = Decimal(balance(client, alice, alice_account)) + Decimal(balance(client, bob, bob_account))
    assert total == Decimal("100.00")
