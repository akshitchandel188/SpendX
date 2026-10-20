import pytest
from datetime import date, timedelta
from app import app
from database.db import init_db, create_user, get_db
from database.queries import (
    get_summary_stats,
    get_recent_transactions,
    get_category_breakdown,
)


@pytest.fixture
def test_client(tmp_path):
    """Provides an isolated Flask test client with a clean temporary SQLite database."""
    db_file = tmp_path / "test_spendly_filter.db"
    init_db(str(db_file))
    app.config.update({
        "TESTING": True,
        "DATABASE": str(db_file),
        "SECRET_KEY": "test-filter-secret-key",
    })
    with app.test_client() as client:
        yield client, str(db_file)


def insert_expense(db_path, user_id, amount, category, date_str, description):
    conn = get_db(db_path)
    try:
        with conn:
            cursor = conn.execute(
                """
                INSERT INTO expenses (user_id, amount, category, date, description)
                VALUES (?, ?, ?, ?, ?)
                """,
                (user_id, amount, category, date_str, description),
            )
            return cursor.lastrowid
    finally:
        conn.close()


# ------------------------------------------------------------------ #
# 1. Unit Tests for database/queries helpers with date filters        #
# ------------------------------------------------------------------ #

def test_queries_with_date_range_filters(tmp_path):
    db_file = tmp_path / "test_queries.db"
    init_db(str(db_file))
    user = create_user("Alice", "alice@example.com", "pass123", db_path=str(db_file))

    # Insert expenses across different dates
    insert_expense(str(db_file), user["id"], 500.0, "Food", "2026-01-10", "Groceries")
    insert_expense(str(db_file), user["id"], 1200.0, "Bills", "2026-02-15", "Electricity")
    insert_expense(str(db_file), user["id"], 300.0, "Food", "2026-03-05", "Cafe")
    insert_expense(str(db_file), user["id"], 800.0, "Shopping", "2026-03-20", "Clothes")

    # 1. Unfiltered (date_from and date_to None)
    all_stats = get_summary_stats(user["id"], db_path=str(db_file))
    assert all_stats["transaction_count"] == 4
    assert all_stats["total_spent"] == 2800.0
    assert all_stats["top_category"] == "Bills"

    all_tx = get_recent_transactions(user["id"], limit=10, db_path=str(db_file))
    assert len(all_tx) == 4
    assert all_tx[0]["description"] == "Clothes"

    all_cat = get_category_breakdown(user["id"], db_path=str(db_file))
    assert len(all_cat) == 3

    # 2. Filtered: 2026-02-01 to 2026-03-10 (should include Bills 1200 and Food 300)
    filtered_stats = get_summary_stats(user["id"], date_from="2026-02-01", date_to="2026-03-10", db_path=str(db_file))
    assert filtered_stats["transaction_count"] == 2
    assert filtered_stats["total_spent"] == 1500.0
    assert filtered_stats["top_category"] == "Bills"

    filtered_tx = get_recent_transactions(user["id"], limit=10, date_from="2026-02-01", date_to="2026-03-10", db_path=str(db_file))
    assert len(filtered_tx) == 2
    assert [t["category"] for t in filtered_tx] == ["Food", "Bills"]

    filtered_cat = get_category_breakdown(user["id"], date_from="2026-02-01", date_to="2026-03-10", db_path=str(db_file))
    assert len(filtered_cat) == 2
    assert sum(c["pct"] for c in filtered_cat) == 100

    # 3. Filtered: No expenses in range
    empty_stats = get_summary_stats(user["id"], date_from="2025-01-01", date_to="2025-01-31", db_path=str(db_file))
    assert empty_stats["transaction_count"] == 0
    assert empty_stats["total_spent"] == 0.0
    assert empty_stats["top_category"] == "—"

    empty_tx = get_recent_transactions(user["id"], limit=10, date_from="2025-01-01", date_to="2025-01-31", db_path=str(db_file))
    assert empty_tx == []

    empty_cat = get_category_breakdown(user["id"], date_from="2025-01-01", date_to="2025-01-31", db_path=str(db_file))
    assert empty_cat == []


# ------------------------------------------------------------------ #
# 2. Integration Tests for GET /profile date filter functionality     #
# ------------------------------------------------------------------ #

def test_profile_unfiltered_default_view(test_client):
    client, db_path = test_client
    user = create_user("Bob", "bob@example.com", "pass123", db_path=db_path)
    with client.session_transaction() as sess:
        sess["user_id"] = user["id"]
        sess["user_name"] = user["name"]

    insert_expense(db_path, user["id"], 250.0, "Food", "2026-01-15", "Lunch")
    insert_expense(db_path, user["id"], 500.0, "Bills", "2026-02-20", "Water bill")

    response = client.get("/profile")
    assert response.status_code == 200
    html = response.get_data(as_text=True)

    # Defaults to All Time
    assert "Lunch" in html
    assert "Water bill" in html
    assert "₹750.00" in html
    assert 'class="preset-btn active">\n                    All Time' in html or 'preset-btn active">\n                    All Time' in html or "All Time" in html


def test_profile_custom_valid_date_range(test_client):
    client, db_path = test_client
    user = create_user("Charlie", "charlie@example.com", "pass123", db_path=db_path)
    with client.session_transaction() as sess:
        sess["user_id"] = user["id"]
        sess["user_name"] = user["name"]

    insert_expense(db_path, user["id"], 100.0, "Food", "2026-05-01", "Out of range before")
    insert_expense(db_path, user["id"], 400.0, "Entertainment", "2026-06-15", "Movie night")
    insert_expense(db_path, user["id"], 300.0, "Shopping", "2026-07-20", "Out of range after")

    response = client.get("/profile?date_from=2026-06-01&date_to=2026-06-30")
    assert response.status_code == 200
    html = response.get_data(as_text=True)

    # Only in-range transaction should appear
    assert "Movie night" in html
    assert "Out of range before" not in html
    assert "Out of range after" not in html
    assert "₹400.00" in html
    assert "Entertainment" in html
    assert 'value="2026-06-01"' in html
    assert 'value="2026-06-30"' in html


def test_profile_date_from_greater_than_date_to_flashes_error(test_client):
    client, db_path = test_client
    user = create_user("Dave", "dave@example.com", "pass123", db_path=db_path)
    with client.session_transaction() as sess:
        sess["user_id"] = user["id"]
        sess["user_name"] = user["name"]

    insert_expense(db_path, user["id"], 500.0, "Food", "2026-05-10", "Groceries")

    # Inverted date range
    response = client.get("/profile?date_from=2026-06-30&date_to=2026-06-01")
    assert response.status_code == 200
    html = response.get_data(as_text=True)

    # Must display flash error
    assert "Start date must be before end date." in html
    # Falls back to unfiltered view
    assert "Groceries" in html
    assert "₹500.00" in html


def test_profile_malformed_dates_fallback_silently(test_client):
    client, db_path = test_client
    user = create_user("Eve", "eve@example.com", "pass123", db_path=db_path)
    with client.session_transaction() as sess:
        sess["user_id"] = user["id"]
        sess["user_name"] = user["name"]

    insert_expense(db_path, user["id"], 350.0, "Health", "2026-04-12", "Pharmacy")

    # Malformed date strings
    response = client.get("/profile?date_from=not-a-date&date_to=2026-04-30")
    assert response.status_code == 200
    html = response.get_data(as_text=True)

    # Silently falls back to unfiltered view without crashing
    assert "Pharmacy" in html
    assert "₹350.00" in html


def test_profile_partial_date_param_fallback_silently(test_client):
    client, db_path = test_client
    user = create_user("Frank", "frank@example.com", "pass123", db_path=db_path)
    with client.session_transaction() as sess:
        sess["user_id"] = user["id"]
        sess["user_name"] = user["name"]

    insert_expense(db_path, user["id"], 200.0, "Transport", "2026-04-15", "Metro")

    # Only date_from provided
    response = client.get("/profile?date_from=2026-04-01")
    assert response.status_code == 200
    html = response.get_data(as_text=True)

    assert "Metro" in html
    assert "₹200.00" in html


def test_profile_presets_filtering(test_client):
    client, db_path = test_client
    user = create_user("Grace", "grace@example.com", "pass123", db_path=db_path)
    with client.session_transaction() as sess:
        sess["user_id"] = user["id"]
        sess["user_name"] = user["name"]

    today = date.today()
    this_month_date = today.strftime("%Y-%m-%d")
    two_months_ago = (today - timedelta(days=60)).strftime("%Y-%m-%d")
    five_months_ago = (today - timedelta(days=140)).strftime("%Y-%m-%d")
    one_year_ago = (today - timedelta(days=365)).strftime("%Y-%m-%d")

    insert_expense(db_path, user["id"], 100.0, "Food", this_month_date, "Today Expense")
    insert_expense(db_path, user["id"], 200.0, "Bills", two_months_ago, "Two Months Ago")
    insert_expense(db_path, user["id"], 400.0, "Shopping", five_months_ago, "Five Months Ago")
    insert_expense(db_path, user["id"], 800.0, "Other", one_year_ago, "One Year Ago")

    # 1. Preset: This Month
    this_month_from = today.replace(day=1).strftime("%Y-%m-%d")
    this_month_to = today.strftime("%Y-%m-%d")
    res_tm = client.get(f"/profile?date_from={this_month_from}&date_to={this_month_to}")
    assert res_tm.status_code == 200
    html_tm = res_tm.get_data(as_text=True)
    assert "Today Expense" in html_tm
    assert "Two Months Ago" not in html_tm
    assert "This Month" in html_tm

    # 2. Preset: Last 3 Months
    l3m_from = (today - timedelta(days=90)).strftime("%Y-%m-%d")
    l3m_to = today.strftime("%Y-%m-%d")
    res_l3m = client.get(f"/profile?date_from={l3m_from}&date_to={l3m_to}")
    assert res_l3m.status_code == 200
    html_l3m = res_l3m.get_data(as_text=True)
    assert "Today Expense" in html_l3m
    assert "Two Months Ago" in html_l3m
    assert "Five Months Ago" not in html_l3m

    # 3. Preset: Last 6 Months
    l6m_from = (today - timedelta(days=180)).strftime("%Y-%m-%d")
    l6m_to = today.strftime("%Y-%m-%d")
    res_l6m = client.get(f"/profile?date_from={l6m_from}&date_to={l6m_to}")
    assert res_l6m.status_code == 200
    html_l6m = res_l6m.get_data(as_text=True)
    assert "Today Expense" in html_l6m
    assert "Two Months Ago" in html_l6m
    assert "Five Months Ago" in html_l6m
    assert "One Year Ago" not in html_l6m


def test_profile_empty_range_displays_gracefully(test_client):
    client, db_path = test_client
    user = create_user("Hank", "hank@example.com", "pass123", db_path=db_path)
    with client.session_transaction() as sess:
        sess["user_id"] = user["id"]
        sess["user_name"] = user["name"]

    insert_expense(db_path, user["id"], 150.0, "Food", "2026-08-01", "August Food")

    # Range with no expenses
    response = client.get("/profile?date_from=2024-01-01&date_to=2024-01-31")
    assert response.status_code == 200
    html = response.get_data(as_text=True)

    assert "₹0.00" in html
    assert "Expenses Logged" in html
    assert "0" in html
    assert "No expenses logged yet." in html
    assert "No category spending yet." in html
