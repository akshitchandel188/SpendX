import sqlite3
import pytest
from datetime import date
from werkzeug.security import check_password_hash
from database.db import (
    get_db,
    init_db,
    seed_db,
    get_user_by_email,
    get_user_by_id,
    create_user,
    get_user_stats,
    get_recent_expenses,
    get_category_spending,
    CATEGORIES,
)


@pytest.fixture
def temp_db(tmp_path):
    """Provides a fresh temporary SQLite database path for isolated testing."""
    db_file = tmp_path / "test_spendly.db"
    return str(db_file)


def test_get_db_connection(temp_db):
    conn = get_db(temp_db)
    try:
        # Check foreign keys PRAGMA is enabled
        cursor = conn.cursor()
        cursor.execute("PRAGMA foreign_keys;")
        row = cursor.fetchone()
        assert row[0] == 1

        # Check row_factory enables dict-like column access
        cursor.execute("SELECT 'Spendly' AS app_name, 42 AS count;")
        result = cursor.fetchone()
        assert isinstance(result, sqlite3.Row)
        assert result["app_name"] == "Spendly"
        assert result["count"] == 42
    finally:
        conn.close()


def test_init_db_creates_tables_and_indexes(temp_db):
    init_db(temp_db)
    conn = get_db(temp_db)
    try:
        cursor = conn.cursor()
        cursor.execute("SELECT name FROM sqlite_master WHERE type='table';")
        tables = [row["name"] for row in cursor.fetchall()]
        assert "users" in tables
        assert "expenses" in tables

        # Verify users columns
        cursor.execute("PRAGMA table_info(users);")
        user_cols = {row["name"]: row["type"] for row in cursor.fetchall()}
        assert "id" in user_cols
        assert "name" in user_cols
        assert "email" in user_cols
        assert "password_hash" in user_cols
        assert "created_at" in user_cols

        # Verify expenses columns
        cursor.execute("PRAGMA table_info(expenses);")
        expense_cols = {row["name"]: row["type"] for row in cursor.fetchall()}
        assert "id" in expense_cols
        assert "user_id" in expense_cols
        assert "amount" in expense_cols
        assert "category" in expense_cols
        assert "date" in expense_cols
        assert "description" in expense_cols
        assert "created_at" in expense_cols

        # Verify indexes
        cursor.execute("SELECT name FROM sqlite_master WHERE type='index';")
        indexes = [row["name"] for row in cursor.fetchall()]
        assert "idx_expenses_user_id" in indexes
        assert "idx_expenses_date" in indexes
    finally:
        conn.close()


def test_init_db_idempotency(temp_db):
    # Calling init_db multiple times should execute cleanly without error
    init_db(temp_db)
    init_db(temp_db)
    init_db(temp_db)


def test_foreign_key_enforcement(temp_db):
    init_db(temp_db)
    conn = get_db(temp_db)
    try:
        cursor = conn.cursor()
        # Attempt to insert expense referencing non-existent user_id
        with pytest.raises(sqlite3.IntegrityError):
            with conn:
                cursor.execute(
                    """
                    INSERT INTO expenses (user_id, amount, category, date, description)
                    VALUES (?, ?, ?, ?, ?);
                    """,
                    (9999, 100.0, "Food", "2026-10-15", "Invalid FK"),
                )
    finally:
        conn.close()


def test_unique_email_constraint(temp_db):
    init_db(temp_db)
    conn = get_db(temp_db)
    try:
        cursor = conn.cursor()
        with conn:
            cursor.execute(
                """
                INSERT INTO users (name, email, password_hash)
                VALUES (?, ?, ?);
                """,
                ("User One", "unique@spendly.com", "hash1"),
            )
        # Duplicate email insert must raise IntegrityError
        with pytest.raises(sqlite3.IntegrityError):
            with conn:
                cursor.execute(
                    """
                    INSERT INTO users (name, email, password_hash)
                    VALUES (?, ?, ?);
                    """,
                    ("User Two", "unique@spendly.com", "hash2"),
                )
    finally:
        conn.close()


def test_category_check_constraint(temp_db):
    init_db(temp_db)
    conn = get_db(temp_db)
    try:
        cursor = conn.cursor()
        with conn:
            cursor.execute(
                """
                INSERT INTO users (name, email, password_hash)
                VALUES (?, ?, ?);
                """,
                ("Valid User", "valid@spendly.com", "hash"),
            )
            user_id = cursor.lastrowid

        # Insert invalid category must raise IntegrityError
        with pytest.raises(sqlite3.IntegrityError):
            with conn:
                cursor.execute(
                    """
                    INSERT INTO expenses (user_id, amount, category, date, description)
                    VALUES (?, ?, ?, ?, ?);
                    """,
                    (user_id, 50.0, "InvalidCategoryName", "2026-10-15", "Should fail"),
                )
    finally:
        conn.close()


def test_seed_db_demo_data(temp_db):
    init_db(temp_db)
    seed_db(temp_db)

    conn = get_db(temp_db)
    try:
        cursor = conn.cursor()

        # Check demo user
        cursor.execute("SELECT * FROM users;")
        users = cursor.fetchall()
        assert len(users) == 1
        demo_user = users[0]
        assert demo_user["name"] == "Demo User"
        assert demo_user["email"] == "demo@spendly.com"
        assert check_password_hash(demo_user["password_hash"], "demo123")

        # Check sample expenses
        cursor.execute("SELECT * FROM expenses WHERE user_id = ?;", (demo_user["id"],))
        expenses = cursor.fetchall()
        assert len(expenses) == 8

        # Verify all categories from CATEGORIES constant are represented
        seeded_categories = {row["category"] for row in expenses}
        for cat in CATEGORIES:
            assert cat in seeded_categories, f"Category {cat} missing from seed expenses"

        # Verify date format and amount types
        today = date.today()
        current_year_month = f"{today.year}-{today.month:02d}"
        for exp in expenses:
            assert isinstance(exp["amount"], float)
            assert exp["amount"] > 0
            assert exp["date"].startswith(current_year_month)
            # Must strictly match YYYY-MM-DD
            parts = exp["date"].split("-")
            assert len(parts) == 3
            assert len(parts[0]) == 4 and len(parts[1]) == 2 and len(parts[2]) == 2
    finally:
        conn.close()


def test_seed_db_idempotency(temp_db):
    init_db(temp_db)
    seed_db(temp_db)
    # Calling seed_db again must not duplicate data
    seed_db(temp_db)

    conn = get_db(temp_db)
    try:
        cursor = conn.cursor()
        cursor.execute("SELECT COUNT(*) AS count FROM users;")
        assert cursor.fetchone()["count"] == 1

        cursor.execute("SELECT COUNT(*) AS count FROM expenses;")
        assert cursor.fetchone()["count"] == 8
    finally:
        conn.close()


def test_app_startup_integration():
    from app import app
    client = app.test_client()
    response = client.get("/")
    assert response.status_code == 200


def test_create_user_and_get_user_by_email(temp_db):
    init_db(temp_db)
    user = create_user("Test User", "test@example.com", "mypassword123", db_path=temp_db)
    assert user is not None
    assert user["name"] == "Test User"
    assert user["email"] == "test@example.com"
    assert user["password_hash"] != "mypassword123"
    assert check_password_hash(user["password_hash"], "mypassword123")

    # Lookup with get_user_by_email
    fetched = get_user_by_email("test@example.com", db_path=temp_db)
    assert fetched is not None
    assert fetched["id"] == user["id"]
    assert fetched["email"] == "test@example.com"

    # Lookup with different case/spaces
    fetched_case = get_user_by_email("  TEST@example.COM ", db_path=temp_db)
    assert fetched_case is not None
    assert fetched_case["id"] == user["id"]

    # Non-existent user
    assert get_user_by_email("nonexistent@example.com", db_path=temp_db) is None
    assert get_user_by_email("", db_path=temp_db) is None


def test_create_user_duplicate_email_raises_error(temp_db):
    init_db(temp_db)
    create_user("User One", "unique@example.com", "pass12345", db_path=temp_db)
    with pytest.raises(sqlite3.IntegrityError):
        create_user("User Two", "unique@example.com", "pass12345", db_path=temp_db)


def test_get_user_by_id(temp_db):
    init_db(temp_db)
    user = create_user("Alice", "alice@example.com", "password123", db_path=temp_db)
    user_id = user["id"]

    # Found case
    found = get_user_by_id(user_id, db_path=temp_db)
    assert found is not None
    assert found["id"] == user_id
    assert found["name"] == "Alice"
    assert found["email"] == "alice@example.com"

    # Not found case
    assert get_user_by_id(99999, db_path=temp_db) is None

    # Falsy/None case
    assert get_user_by_id(None, db_path=temp_db) is None
    assert get_user_by_id(0, db_path=temp_db) is None


def test_get_user_stats_empty(temp_db):
    init_db(temp_db)
    user = create_user("No Expense User", "noexpense@example.com", "password123", db_path=temp_db)
    stats = get_user_stats(user["id"], db_path=temp_db)
    assert stats["total_count"] == 0
    assert stats["total_amount"] == 0.0


def test_get_user_stats_with_data(temp_db):
    init_db(temp_db)
    user = create_user("Spender", "spender@example.com", "password123", db_path=temp_db)
    conn = get_db(temp_db)
    try:
        with conn:
            conn.execute(
                """
                INSERT INTO expenses (user_id, amount, category, date, description)
                VALUES (?, ?, ?, ?, ?), (?, ?, ?, ?, ?), (?, ?, ?, ?, ?);
                """,
                (
                    user["id"], 250.50, "Food", "2026-10-01", "Lunch",
                    user["id"], 100.00, "Transport", "2026-10-02", "Bus",
                    user["id"], 749.50, "Shopping", "2026-10-03", "Clothes",
                ),
            )
    finally:
        conn.close()

    stats = get_user_stats(user["id"], db_path=temp_db)
    assert stats["total_count"] == 3
    assert stats["total_amount"] == pytest.approx(1100.00)


def test_get_user_stats_isolation(temp_db):
    init_db(temp_db)
    user1 = create_user("User One", "user1@example.com", "password123", db_path=temp_db)
    user2 = create_user("User Two", "user2@example.com", "password123", db_path=temp_db)

    conn = get_db(temp_db)
    try:
        with conn:
            conn.execute(
                """
                INSERT INTO expenses (user_id, amount, category, date, description)
                VALUES (?, ?, ?, ?, ?), (?, ?, ?, ?, ?);
                """,
                (
                    user1["id"], 500.00, "Bills", "2026-10-05", "User1 electricity",
                    user2["id"], 1500.00, "Rent" if "Rent" in CATEGORIES else "Other", "2026-10-05", "User2 other",
                ),
            )
    finally:
        conn.close()

    stats1 = get_user_stats(user1["id"], db_path=temp_db)
    assert stats1["total_count"] == 1
    assert stats1["total_amount"] == pytest.approx(500.00)

    stats2 = get_user_stats(user2["id"], db_path=temp_db)
    assert stats2["total_count"] == 1
    assert stats2["total_amount"] == pytest.approx(1500.00)


def test_get_user_stats_none_or_invalid_id(temp_db):
    init_db(temp_db)
    assert get_user_stats(None, db_path=temp_db) == {"total_count": 0, "total_amount": 0.0}
    assert get_user_stats(0, db_path=temp_db) == {"total_count": 0, "total_amount": 0.0}
    assert get_user_stats(99999, db_path=temp_db) == {"total_count": 0, "total_amount": 0.0}


def test_get_recent_expenses(temp_db):
    init_db(temp_db)
    user = create_user("Recent Spender", "recent@example.com", "password123", db_path=temp_db)
    conn = get_db(temp_db)
    try:
        with conn:
            conn.execute(
                """
                INSERT INTO expenses (user_id, amount, category, date, description)
                VALUES (?, ?, ?, ?, ?), (?, ?, ?, ?, ?), (?, ?, ?, ?, ?);
                """,
                (
                    user["id"], 100.0, "Food", "2026-10-01", "Oldest",
                    user["id"], 200.0, "Bills", "2026-10-02", "Middle",
                    user["id"], 300.0, "Shopping", "2026-10-03", "Newest",
                ),
            )
    finally:
        conn.close()

    # Default limit=5 returns all 3, ordered date DESC
    recent = get_recent_expenses(user["id"], db_path=temp_db)
    assert len(recent) == 3
    assert recent[0]["description"] == "Newest"
    assert recent[1]["description"] == "Middle"
    assert recent[2]["description"] == "Oldest"

    # Limit=2 returns latest 2
    limited = get_recent_expenses(user["id"], limit=2, db_path=temp_db)
    assert len(limited) == 2
    assert limited[0]["description"] == "Newest"

    # Invalid / None user
    assert get_recent_expenses(None, db_path=temp_db) == []
    assert get_recent_expenses(0, db_path=temp_db) == []


def test_get_category_spending(temp_db):
    init_db(temp_db)
    user = create_user("Category Spender", "catspender@example.com", "password123", db_path=temp_db)
    conn = get_db(temp_db)
    try:
        with conn:
            conn.execute(
                """
                INSERT INTO expenses (user_id, amount, category, date, description)
                VALUES (?, ?, ?, ?, ?), (?, ?, ?, ?, ?), (?, ?, ?, ?, ?);
                """,
                (
                    user["id"], 500.0, "Food", "2026-10-01", "Lunch",
                    user["id"], 250.0, "Food", "2026-10-02", "Dinner",
                    user["id"], 1500.0, "Shopping", "2026-10-03", "Shoes",
                ),
            )
    finally:
        conn.close()

    cat_spending = get_category_spending(user["id"], db_path=temp_db)
    # Sorted descending: Shopping (1500) then Food (750)
    assert len(cat_spending) == 2
    assert cat_spending[0]["category"] == "Shopping"
    assert cat_spending[0]["total_amount"] == 1500.0
    assert cat_spending[0]["count"] == 1
    assert cat_spending[0]["relative_pct"] == 100.0

    assert cat_spending[1]["category"] == "Food"
    assert cat_spending[1]["total_amount"] == 750.0
    assert cat_spending[1]["count"] == 2
    assert cat_spending[1]["relative_pct"] == 50.0

    # User with no expenses or invalid user
    assert get_category_spending(None, db_path=temp_db) == []
    assert get_category_spending(99999, db_path=temp_db) == []





