import sqlite3
import pytest
from datetime import date
from werkzeug.security import check_password_hash
from database.db import get_db, init_db, seed_db, CATEGORIES


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
