import pytest
from werkzeug.security import check_password_hash
from app import app
from database.db import init_db, get_user_by_email


@pytest.fixture
def test_client(tmp_path):
    """Provides an isolated Flask test client with a clean temporary SQLite database."""
    db_file = tmp_path / "test_spendly.db"
    init_db(str(db_file))
    app.config.update({
        "TESTING": True,
        "DATABASE": str(db_file),
    })
    with app.test_client() as client:
        yield client, str(db_file)


def test_register_get_renders_form(test_client):
    client, _ = test_client
    response = client.get("/register")
    assert response.status_code == 200
    html = response.get_data(as_text=True)
    assert "Create your account" in html
    assert 'action="/register"' in html
    assert 'name="name"' in html
    assert 'name="email"' in html
    assert 'name="password"' in html


def test_register_post_success_redirects_and_creates_user(test_client):
    client, db_path = test_client
    response = client.post(
        "/register",
        data={
            "name": "Jane Doe",
            "email": "jane.doe@example.com",
            "password": "securepassword123",
        },
    )
    # Check redirect to /login
    assert response.status_code == 302
    assert response.headers["Location"].endswith("/login")

    # Check database persistence
    user = get_user_by_email("jane.doe@example.com", db_path=db_path)
    assert user is not None
    assert user["name"] == "Jane Doe"
    assert user["email"] == "jane.doe@example.com"
    assert user["password_hash"] != "securepassword123"
    assert check_password_hash(user["password_hash"], "securepassword123")


def test_register_post_email_normalized(test_client):
    client, db_path = test_client
    response = client.post(
        "/register",
        data={
            "name": "  Alice Smith  ",
            "email": "   ALICE.Smith@Example.COM   ",
            "password": "password888",
        },
    )
    assert response.status_code == 302

    # Verify normalized in DB
    user = get_user_by_email("alice.smith@example.com", db_path=db_path)
    assert user is not None
    assert user["name"] == "Alice Smith"
    assert user["email"] == "alice.smith@example.com"


@pytest.mark.parametrize("payload", [
    {"name": "", "email": "valid@example.com", "password": "password123"},
    {"name": "   ", "email": "valid@example.com", "password": "password123"},
    {"name": "Valid Name", "email": "", "password": "password123"},
    {"name": "Valid Name", "email": "   ", "password": "password123"},
    {"name": "Valid Name", "email": "valid@example.com", "password": ""},
])
def test_register_missing_fields_returns_400(test_client, payload):
    client, _ = test_client
    response = client.post("/register", data=payload)
    assert response.status_code == 400
    html = response.get_data(as_text=True)
    assert "All fields are required." in html


@pytest.mark.parametrize("invalid_email", [
    "notanemail",
    "missingat.com",
    "@nodomain.com",
    "user@.com",
    "user@domain",
    "user name@domain.com",
])
def test_register_invalid_email_format_returns_400(test_client, invalid_email):
    client, _ = test_client
    response = client.post(
        "/register",
        data={
            "name": "John Doe",
            "email": invalid_email,
            "password": "password123",
        },
    )
    assert response.status_code == 400
    html = response.get_data(as_text=True)
    assert "Please enter a valid email address." in html
    assert 'value="John Doe"' in html


def test_register_password_too_short_returns_400(test_client):
    client, _ = test_client
    response = client.post(
        "/register",
        data={
            "name": "John Doe",
            "email": "john@example.com",
            "password": "short",
        },
    )
    assert response.status_code == 400
    html = response.get_data(as_text=True)
    assert "Password must be at least 8 characters long." in html
    # Preserves entered name and email
    assert 'value="John Doe"' in html
    assert 'value="john@example.com"' in html
    # Password field should not retain value
    assert 'value="short"' not in html


def test_register_duplicate_email_returns_400(test_client):
    client, db_path = test_client
    # Register first user
    first_response = client.post(
        "/register",
        data={
            "name": "First User",
            "email": "duplicate@example.com",
            "password": "password123",
        },
    )
    assert first_response.status_code == 302

    # Attempt second registration with same email (different casing)
    second_response = client.post(
        "/register",
        data={
            "name": "Second User",
            "email": "  DUPLICATE@example.COM  ",
            "password": "newpassword123",
        },
    )
    assert second_response.status_code == 400
    html = second_response.get_data(as_text=True)
    assert "An account with this email already exists." in html
    assert 'value="Second User"' in html
