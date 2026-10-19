import pytest
from app import app
from database.db import init_db, create_user


@pytest.fixture
def test_client(tmp_path):
    """Provides an isolated Flask test client with a clean temporary SQLite database."""
    db_file = tmp_path / "test_spendly.db"
    init_db(str(db_file))
    app.config.update({
        "TESTING": True,
        "DATABASE": str(db_file),
        "SECRET_KEY": "test-auth-secret-key",
    })
    with app.test_client() as client:
        yield client, str(db_file)


def test_login_get_renders_form(test_client):
    client, _ = test_client
    response = client.get("/login")
    assert response.status_code == 200
    html = response.get_data(as_text=True)
    assert "Sign in to your Spendly account" in html
    assert 'action="/login"' in html
    assert 'name="email"' in html
    assert 'name="password"' in html


def test_login_already_authenticated_redirects(test_client):
    client, db_path = test_client
    user = create_user("Existing User", "existing@example.com", "password123", db_path=db_path)

    with client.session_transaction() as sess:
        sess["user_id"] = user["id"]
        sess["user_name"] = user["name"]

    response = client.get("/login")
    assert response.status_code == 302
    assert response.headers["Location"].endswith("/profile")


@pytest.mark.parametrize("payload", [
    {"email": "", "password": "password123"},
    {"email": "   ", "password": "password123"},
    {"email": "user@example.com", "password": ""},
    {"email": "", "password": ""},
])
def test_login_missing_fields_returns_400(test_client, payload):
    client, _ = test_client
    response = client.post("/login", data=payload)
    assert response.status_code == 400
    html = response.get_data(as_text=True)
    assert "All fields are required." in html


def test_login_nonexistent_email_returns_401(test_client):
    client, _ = test_client
    response = client.post(
        "/login",
        data={
            "email": "notfound@example.com",
            "password": "somepassword123",
        },
    )
    assert response.status_code == 401
    html = response.get_data(as_text=True)
    assert "Invalid email or password." in html
    assert 'value="notfound@example.com"' in html


def test_login_wrong_password_returns_401(test_client):
    client, db_path = test_client
    create_user("Bob", "bob@example.com", "correctpassword123", db_path=db_path)

    response = client.post(
        "/login",
        data={
            "email": "bob@example.com",
            "password": "wrongpassword999",
        },
    )
    assert response.status_code == 401
    html = response.get_data(as_text=True)
    assert "Invalid email or password." in html
    assert 'value="bob@example.com"' in html
    assert 'wrongpassword999' not in html


def test_login_success_sets_session_and_redirects(test_client):
    client, db_path = test_client
    user = create_user("Charlie", "charlie@example.com", "mypassword123", db_path=db_path)

    response = client.post(
        "/login",
        data={
            "email": "charlie@example.com",
            "password": "mypassword123",
        },
    )
    assert response.status_code == 302
    assert response.headers["Location"].endswith("/profile")

    with client.session_transaction() as sess:
        assert sess.get("user_id") == user["id"]
        assert sess.get("user_name") == "Charlie"


def test_login_email_normalized(test_client):
    client, db_path = test_client
    user = create_user("Dana", "dana@example.com", "mypassword123", db_path=db_path)

    response = client.post(
        "/login",
        data={
            "email": "   DANA@EXAMPLE.COM   ",
            "password": "mypassword123",
        },
    )
    assert response.status_code == 302
    assert response.headers["Location"].endswith("/profile")

    with client.session_transaction() as sess:
        assert sess.get("user_id") == user["id"]


def test_logout_clears_session_and_redirects(test_client):
    client, db_path = test_client
    user = create_user("Evan", "evan@example.com", "mypassword123", db_path=db_path)

    with client.session_transaction() as sess:
        sess["user_id"] = user["id"]
        sess["user_name"] = user["name"]

    response = client.get("/logout")
    assert response.status_code == 302
    assert response.headers["Location"].endswith("/login")

    with client.session_transaction() as sess:
        assert "user_id" not in sess
        assert "user_name" not in sess


def test_navbar_unauthenticated_state(test_client):
    client, _ = test_client
    response = client.get("/")
    assert response.status_code == 200
    html = response.get_data(as_text=True)
    assert "Sign in" in html
    assert "Get started" in html
    assert "Sign out" not in html


def test_navbar_authenticated_state(test_client):
    client, db_path = test_client
    user = create_user("Fiona", "fiona@example.com", "mypassword123", db_path=db_path)

    with client.session_transaction() as sess:
        sess["user_id"] = user["id"]
        sess["user_name"] = user["name"]

    response = client.get("/")
    assert response.status_code == 200
    html = response.get_data(as_text=True)
    assert "Sign out" in html
    assert "Fiona" in html
    assert "Sign in" not in html
    assert "Get started" not in html
