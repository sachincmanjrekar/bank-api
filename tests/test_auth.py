def test_health(client):
    response = client.get("/health")
    assert response.status_code == 200
    assert response.json() == {"status": "ok"}


def test_register_returns_user_without_password(client):
    response = client.post(
        "/auth/register",
        json={"email": "new@example.com", "full_name": "New User", "password": "password123"},
    )
    assert response.status_code == 201
    body = response.json()
    assert body["email"] == "new@example.com"
    assert "password" not in body
    assert "hashed_password" not in body


def test_register_duplicate_email_is_rejected(client, alice):
    response = client.post(
        "/auth/register",
        json={"email": "alice@example.com", "full_name": "Again", "password": "password123"},
    )
    assert response.status_code == 409


def test_register_short_password_is_rejected(client):
    response = client.post(
        "/auth/register",
        json={"email": "x@example.com", "full_name": "X", "password": "short"},
    )
    assert response.status_code == 422


def test_login_wrong_password(client, alice):
    response = client.post(
        "/auth/login", data={"username": "alice@example.com", "password": "wrong-password"}
    )
    assert response.status_code == 401


def test_login_unknown_email_gives_same_error_as_wrong_password(client):
    response = client.post(
        "/auth/login", data={"username": "nobody@example.com", "password": "password123"}
    )
    assert response.status_code == 401
    assert response.json()["detail"] == "Invalid email or password"


def test_me_returns_logged_in_user(client, alice):
    response = client.get("/auth/me", headers=alice)
    assert response.status_code == 200
    assert response.json()["email"] == "alice@example.com"


def test_me_without_token(client):
    assert client.get("/auth/me").status_code == 401


def test_me_with_tampered_token(client):
    response = client.get("/auth/me", headers={"Authorization": "Bearer not-a-real-token"})
    assert response.status_code == 401
