import pytest
from app import app
from database.db import init_db, seed_db, create_user, get_db
from database.queries import (
    get_user_by_id,
    get_summary_stats,
    get_recent_transactions,
    get_category_breakdown,
)


@pytest.fixture
def test_client(tmp_path):
    """Provides a fresh test client and SQLite database with seed data."""
    db_file = tmp_path / "test_spendly_backend.db"
    init_db(str(db_file))
    seed_db(str(db_file))
    app.config.update({
        "TESTING": True,
        "DATABASE": str(db_file),
        "SECRET_KEY": "test-backend-connection-secret",
    })
    with app.test_client() as client:
        yield client, str(db_file)


# ------------------------------------------------------------------ #
# Unit tests for query helpers                                       #
# ------------------------------------------------------------------ #

def test_query_get_user_by_id(test_client):
    _, db_path = test_client
    # Seed user id is 1
    user = get_user_by_id(1, db_path=db_path)
    assert user is not None
    assert user["name"] == "Demo User"
    assert user["email"] == "demo@spendly.com"
    assert "member_since" in user

    # Non-existent id
    assert get_user_by_id(9999, db_path=db_path) is None


def test_query_get_summary_stats_seed_user(test_client):
    _, db_path = test_client
    stats = get_summary_stats(1, db_path=db_path)
    # Seed data has 8 transactions
    assert stats["transaction_count"] == 8
    # 350 + 120.50 + 1200 + 450 + 500 + 899 + 180 + 250 = 3949.50
    assert stats["total_spent"] == 3949.50
    # Bills has 1200.00 (highest single category)
    assert stats["top_category"] == "Bills"


def test_query_get_summary_stats_zero_expenses(test_client):
    _, db_path = test_client
    new_user = create_user("Zero", "zero@spendly.com", "pass123", db_path=db_path)
    stats = get_summary_stats(new_user["id"], db_path=db_path)
    assert stats["total_spent"] == 0.0
    assert stats["transaction_count"] == 0
    assert stats["top_category"] == "—"


def test_query_get_recent_transactions(test_client):
    _, db_path = test_client
    txs = get_recent_transactions(1, limit=10, db_path=db_path)
    assert len(txs) == 8
    # Verify newest-first order
    dates = [t["date"] for t in txs]
    assert dates == sorted(dates, reverse=True)
    for t in txs:
        assert "amount" in t
        assert "category" in t
        assert "date" in t


def test_query_get_recent_transactions_empty(test_client):
    _, db_path = test_client
    new_user = create_user("Empty", "empty@spendly.com", "pass123", db_path=db_path)
    assert get_recent_transactions(new_user["id"], db_path=db_path) == []


def test_query_get_category_breakdown(test_client):
    _, db_path = test_client
    breakdown = get_category_breakdown(1, db_path=db_path)
    # Seed data covers all 7 categories
    assert len(breakdown) == 7
    # Ordered descending by amount
    amounts = [b["amount"] for b in breakdown]
    assert amounts == sorted(amounts, reverse=True)
    # Highest category is Bills (1200.0)
    assert breakdown[0]["name"] == "Bills"
    assert breakdown[0]["amount"] == 1200.0
    # Integer percentages must sum to 100
    assert sum(b["pct"] for b in breakdown) == 100


def test_query_get_category_breakdown_empty(test_client):
    _, db_path = test_client
    new_user = create_user("NoSpend", "nospend@spendly.com", "pass123", db_path=db_path)
    assert get_category_breakdown(new_user["id"], db_path=db_path) == []


# ------------------------------------------------------------------ #
# Route tests for GET /profile                                       #
# ------------------------------------------------------------------ #

def test_profile_unauthenticated(test_client):
    client, _ = test_client
    res = client.get("/profile")
    assert res.status_code == 302
    assert res.headers["Location"].endswith("/login")


def test_profile_authenticated_seed_user(test_client):
    client, _ = test_client
    with client.session_transaction() as sess:
        sess["user_id"] = 1
        sess["user_name"] = "Demo User"

    res = client.get("/profile")
    assert res.status_code == 200
    html = res.get_data(as_text=True)

    # Name and Email
    assert "Demo User" in html
    assert "demo@spendly.com" in html

    # Currency symbol
    assert "₹" in html

    # Summary metrics
    assert "8" in html
    assert "3,949.50" in html
    assert "Bills" in html
    assert "Top Category" in html

    # Recent transactions
    assert "Recent Transactions" in html
    assert "Electricity" in html or "Monthly electricity bill" in html

    # Category breakdown
    assert "By Category" in html


def test_profile_authenticated_new_user_zero_expenses(test_client):
    client, db_path = test_client
    new_user = create_user("Brand New", "new@spendly.com", "secretpass123", db_path=db_path)

    with client.session_transaction() as sess:
        sess["user_id"] = new_user["id"]
        sess["user_name"] = new_user["name"]

    res = client.get("/profile")
    assert res.status_code == 200
    html = res.get_data(as_text=True)

    assert "Brand New" in html
    assert "new@spendly.com" in html
    assert "₹0.00" in html
    assert "0" in html
    assert "No expenses logged yet." in html
    assert "No category spending yet." in html
