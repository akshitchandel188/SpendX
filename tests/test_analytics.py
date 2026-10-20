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
        "SECRET_KEY": "test-analytics-secret-key",
    })
    with app.test_client() as client:
        yield client, str(db_file)


def test_analytics_unauthenticated_redirects_to_login(test_client):
    """Unauthenticated users should be redirected to login when visiting /analytics."""
    client, _ = test_client
    response = client.get("/analytics")
    assert response.status_code == 302
    assert response.headers["Location"].endswith("/login")


def test_analytics_authenticated_renders_coming_soon(test_client):
    """Authenticated users should see the Coming Soon analytics page."""
    client, db_path = test_client
    user = create_user("Aarav Mehta", "aarav@example.com", "securepass123", db_path=db_path)

    with client.session_transaction() as sess:
        sess["user_id"] = user["id"]
        sess["user_name"] = user["name"]

    response = client.get("/analytics")
    assert response.status_code == 200
    html = response.get_data(as_text=True)

    assert "Analytics — Spendly" in html
    assert "Advanced Analytics" in html
    assert "Coming Soon" in html
    assert "We're working on powerful insights and visualizations to help you understand your spending patterns better." in html
    assert "We're crafting something special" in html
    assert "analytics.css" in html


def test_analytics_stale_session_redirects_and_clears(test_client):
    """Stale sessions with non-existent user_id should be cleared and redirected to login."""
    client, _ = test_client

    with client.session_transaction() as sess:
        sess["user_id"] = 99999
        sess["user_name"] = "Ghost User"

    response = client.get("/analytics")
    assert response.status_code == 302
    assert response.headers["Location"].endswith("/login")

    with client.session_transaction() as sess:
        assert "user_id" not in sess


def test_navbar_analytics_link_hidden_for_unauthenticated_user(test_client):
    """Navbar should NOT show Analytics link when user is logged out."""
    client, _ = test_client
    response = client.get("/")
    assert response.status_code == 200
    html = response.get_data(as_text=True)

    assert 'href="/analytics"' not in html
    assert "Analytics" not in html


def test_navbar_analytics_link_visible_for_authenticated_user(test_client):
    """Navbar should show Analytics link when user is logged in."""
    client, db_path = test_client
    user = create_user("Priya Sharma", "priya@example.com", "securepass123", db_path=db_path)

    with client.session_transaction() as sess:
        sess["user_id"] = user["id"]
        sess["user_name"] = user["name"]

    response = client.get("/")
    assert response.status_code == 200
    html = response.get_data(as_text=True)

    assert 'href="/analytics"' in html
    assert "Analytics" in html


def test_navbar_analytics_active_highlight_on_analytics_page(test_client):
    """Active class should be present on Analytics link only when on /analytics."""
    client, db_path = test_client
    user = create_user("Rohan Patel", "rohan@example.com", "securepass123", db_path=db_path)

    with client.session_transaction() as sess:
        sess["user_id"] = user["id"]
        sess["user_name"] = user["name"]

    # On /analytics: active class is present
    response = client.get("/analytics")
    assert response.status_code == 200
    html = response.get_data(as_text=True)
    assert 'href="/analytics" class="active"' in html

    # On /profile: active class is not on Analytics link
    response = client.get("/profile")
    assert response.status_code == 200
    html = response.get_data(as_text=True)
    assert 'href="/analytics" class="active"' not in html
    assert 'href="/analytics" class=""' in html
