import pytest
from app import app
from database.db import init_db, create_user, get_db


@pytest.fixture
def test_client(tmp_path):
    """Provides an isolated Flask test client with a clean temporary SQLite database."""
    db_file = tmp_path / "test_spendly.db"
    init_db(str(db_file))
    app.config.update({
        "TESTING": True,
        "DATABASE": str(db_file),
        "SECRET_KEY": "test-profile-secret-key",
    })
    with app.test_client() as client:
        yield client, str(db_file)


def test_profile_unauthenticated_redirects_to_login(test_client):
    client, _ = test_client
    response = client.get("/profile")
    assert response.status_code == 302
    assert response.headers["Location"].endswith("/login")


def test_profile_authenticated_renders_200(test_client):
    client, db_path = test_client
    user = create_user("Rahul Sharma", "rahul@example.com", "securepass123", db_path=db_path)

    with client.session_transaction() as sess:
        sess["user_id"] = user["id"]
        sess["user_name"] = user["name"]

    response = client.get("/profile")
    assert response.status_code == 200
    html = response.get_data(as_text=True)
    assert "Profile — Spendly" in html
    assert "Rahul Sharma" in html
    assert "rahul@example.com" in html


def test_profile_displays_user_details_and_initials(test_client):
    client, db_path = test_client
    user = create_user("Aarav Mehta", "aarav.mehta@example.com", "securepass123", db_path=db_path)

    with client.session_transaction() as sess:
        sess["user_id"] = user["id"]
        sess["user_name"] = user["name"]

    response = client.get("/profile")
    assert response.status_code == 200
    html = response.get_data(as_text=True)

    # Initials badge should be AM
    assert "AM" in html
    assert "Aarav Mehta" in html
    assert "aarav.mehta@example.com" in html
    assert f"#{user['id']}" in html
    assert "Active Member" in html
    assert "Account Details" in html


def test_profile_zero_expenses_display(test_client):
    client, db_path = test_client
    user = create_user("New User", "newbie@example.com", "securepass123", db_path=db_path)

    with client.session_transaction() as sess:
        sess["user_id"] = user["id"]
        sess["user_name"] = user["name"]

    response = client.get("/profile")
    assert response.status_code == 200
    html = response.get_data(as_text=True)

    assert "Expenses Logged" in html
    assert "0" in html
    assert "₹0.00" in html
    assert "No expenses logged yet." in html


def test_profile_aggregated_stats_display(test_client):
    client, db_path = test_client
    user = create_user("Active Spender", "spender@example.com", "securepass123", db_path=db_path)

    # Insert sample expenses
    conn = get_db(db_path)
    try:
        with conn:
            conn.execute(
                """
                INSERT INTO expenses (user_id, amount, category, date, description)
                VALUES (?, ?, ?, ?, ?), (?, ?, ?, ?, ?);
                """,
                (
                    user["id"], 450.50, "Food", "2026-10-10", "Dinner",
                    user["id"], 800.00, "Bills", "2026-10-12", "Wifi",
                ),
            )
    finally:
        conn.close()

    with client.session_transaction() as sess:
        sess["user_id"] = user["id"]
        sess["user_name"] = user["name"]

    response = client.get("/profile")
    assert response.status_code == 200
    html = response.get_data(as_text=True)

    # Count is 2, sum is 1,250.50
    assert "2" in html
    assert "₹1,250.50" in html
    assert "Recent Transactions" in html
    assert "By Category" in html
    assert "Dinner" in html
    assert "Wifi" in html


def test_profile_stale_session_clears_and_redirects(test_client):
    client, _ = test_client

    with client.session_transaction() as sess:
        sess["user_id"] = 99999  # Non-existent user
        sess["user_name"] = "Ghost User"

    response = client.get("/profile")
    assert response.status_code == 302
    assert response.headers["Location"].endswith("/login")

    # Verify session was cleared
    with client.session_transaction() as sess:
        assert "user_id" not in sess


def test_navbar_profile_link(test_client):
    client, db_path = test_client
    user = create_user("Nav User", "nav@example.com", "securepass123", db_path=db_path)

    with client.session_transaction() as sess:
        sess["user_id"] = user["id"]
        sess["user_name"] = user["name"]

    response = client.get("/")
    assert response.status_code == 200
    html = response.get_data(as_text=True)

    # The user name should be inside an anchor linking to /profile
    assert 'href="/profile"' in html
    assert "Nav User" in html
