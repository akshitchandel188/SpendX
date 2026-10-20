import sqlite3
from datetime import date
from pathlib import Path
from flask import current_app, has_app_context
from werkzeug.security import generate_password_hash

BASE_DIR = Path(__file__).resolve().parent.parent
DEFAULT_DB_PATH = BASE_DIR / "spendly.db"

CATEGORIES = (
    "Food",
    "Transport",
    "Bills",
    "Health",
    "Entertainment",
    "Shopping",
    "Other",
)


def get_db_path(db_path=None):
    """Resolve the SQLite database file path."""
    if db_path is not None:
        return Path(db_path)
    if has_app_context() and current_app.config.get("DATABASE"):
        return Path(current_app.config["DATABASE"])
    return DEFAULT_DB_PATH


def get_db(db_path=None):
    """
    Open and return a SQLite database connection with row_factory set to sqlite3.Row
    and foreign key constraints enabled via PRAGMA foreign_keys = ON.
    """
    target_path = get_db_path(db_path)
    conn = sqlite3.connect(target_path)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON;")
    return conn


def init_db(db_path=None):
    """
    Create all tables (users and expenses) and indexes using CREATE TABLE IF NOT EXISTS.
    Idempotent and safe to run multiple times.
    """
    conn = get_db(db_path)
    try:
        with conn:
            conn.execute("""
                CREATE TABLE IF NOT EXISTS users (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    name TEXT NOT NULL,
                    email TEXT UNIQUE NOT NULL,
                    password_hash TEXT NOT NULL,
                    created_at TEXT DEFAULT (datetime('now'))
                );
            """)
            conn.execute("""
                CREATE TABLE IF NOT EXISTS expenses (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    user_id INTEGER NOT NULL,
                    amount REAL NOT NULL,
                    category TEXT NOT NULL CHECK (category IN (
                        'Food', 'Transport', 'Bills', 'Health', 'Entertainment', 'Shopping', 'Other'
                    )),
                    date TEXT NOT NULL,
                    description TEXT,
                    created_at TEXT DEFAULT (datetime('now')),
                    FOREIGN KEY (user_id) REFERENCES users (id) ON DELETE CASCADE
                );
            """)
            conn.execute("CREATE INDEX IF NOT EXISTS idx_expenses_user_id ON expenses(user_id);")
            conn.execute("CREATE INDEX IF NOT EXISTS idx_expenses_date ON expenses(date);")
            conn.execute("CREATE INDEX IF NOT EXISTS idx_expenses_user_date ON expenses(user_id, date);")
    finally:
        conn.close()


def seed_db(db_path=None):
    """
    Seed the database with a demo user and 8 sample expenses across all 7 categories.
    Idempotent: returns early without modifying data if users table already contains records.
    """
    conn = get_db(db_path)
    try:
        cursor = conn.cursor()
        cursor.execute("SELECT COUNT(*) AS count FROM users;")
        row = cursor.fetchone()
        if row and row["count"] > 0:
            return

        with conn:
            # 1. Insert demo user
            hashed_pw = generate_password_hash("demo123")
            cursor.execute(
                """
                INSERT INTO users (name, email, password_hash)
                VALUES (?, ?, ?);
                """,
                ("Demo User", "demo@spendly.com", hashed_pw),
            )
            demo_user_id = cursor.lastrowid

            # 2. Insert 8 sample expenses across current month
            today = date.today()
            year = today.year
            month = today.month

            sample_expenses = [
                (demo_user_id, 350.00, "Food", f"{year}-{month:02d}-02", "Grocery shopping at supermarket"),
                (demo_user_id, 120.50, "Transport", f"{year}-{month:02d}-05", "Metro card recharge"),
                (demo_user_id, 1200.00, "Bills", f"{year}-{month:02d}-08", "Monthly electricity bill"),
                (demo_user_id, 450.00, "Health", f"{year}-{month:02d}-12", "Pharmacy medicines"),
                (demo_user_id, 500.00, "Entertainment", f"{year}-{month:02d}-15", "Movie tickets and snacks"),
                (demo_user_id, 899.00, "Shopping", f"{year}-{month:02d}-18", "New running shoes"),
                (demo_user_id, 180.00, "Food", f"{year}-{month:02d}-22", "Lunch with colleagues"),
                (demo_user_id, 250.00, "Other", f"{year}-{month:02d}-25", "Stationery and desk supplies"),
            ]

            cursor.executemany(
                """
                INSERT INTO expenses (user_id, amount, category, date, description)
                VALUES (?, ?, ?, ?, ?);
                """,
                sample_expenses,
            )
    finally:
        conn.close()


def get_user_by_email(email, db_path=None):
    """
    Look up an existing user by normalized email.
    Returns sqlite3.Row if found, otherwise None.
    """
    normalized_email = email.strip().lower() if email else ""
    if not normalized_email:
        return None
    conn = get_db(db_path)
    try:
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM users WHERE email = ?;", (normalized_email,))
        return cursor.fetchone()
    finally:
        conn.close()


def get_user_by_id(user_id, db_path=None):
    """
    Look up an existing user by primary key ID.
    Returns sqlite3.Row if found, otherwise None.
    """
    if not user_id:
        return None
    conn = get_db(db_path)
    try:
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM users WHERE id = ?;", (user_id,))
        return cursor.fetchone()
    finally:
        conn.close()


def create_user(name, email, password, db_path=None):
    """
    Hash password and insert a new user record using parameterized SQL.
    Returns the newly created user as a sqlite3.Row.
    """
    normalized_name = name.strip()
    normalized_email = email.strip().lower()
    password_hash = generate_password_hash(password)

    conn = get_db(db_path)
    try:
        with conn:
            cursor = conn.cursor()
            cursor.execute(
                """
                INSERT INTO users (name, email, password_hash)
                VALUES (?, ?, ?);
                """,
                (normalized_name, normalized_email, password_hash),
            )
            user_id = cursor.lastrowid
            cursor.execute("SELECT * FROM users WHERE id = ?;", (user_id,))
            return cursor.fetchone()
    finally:
        conn.close()


def get_user_stats(user_id, db_path=None):
    """
    Query aggregate expense statistics for a user (total expense count and sum of amounts).
    Returns a dict with 'total_count' (int) and 'total_amount' (float).
    Handles users with zero expenses gracefully returning 0 and 0.0.
    """
    if not user_id:
        return {"total_count": 0, "total_amount": 0.0}

    conn = get_db(db_path)
    try:
        cursor = conn.cursor()
        cursor.execute(
            """
            SELECT
                COUNT(*) AS total_count,
                COALESCE(SUM(amount), 0.0) AS total_amount
            FROM expenses
            WHERE user_id = ?;
            """,
            (user_id,),
        )
        row = cursor.fetchone()
        if row:
            return {
                "total_count": int(row["total_count"]),
                "total_amount": float(row["total_amount"]),
            }
        return {"total_count": 0, "total_amount": 0.0}
    finally:
        conn.close()


def get_recent_expenses(user_id, limit=5, db_path=None):
    """
    Fetch the most recent expenses for a user ordered by date DESC, id DESC.
    Returns a list of sqlite3.Row objects.
    """
    if not user_id:
        return []
    conn = get_db(db_path)
    try:
        cursor = conn.cursor()
        cursor.execute(
            """
            SELECT id, amount, category, date, description
            FROM expenses
            WHERE user_id = ?
            ORDER BY date DESC, id DESC
            LIMIT ?;
            """,
            (user_id, limit),
        )
        return cursor.fetchall()
    finally:
        conn.close()


def get_category_spending(user_id, db_path=None):
    """
    Query total spending grouped by category for a user, sorted descending by total amount.
    Returns a list of dicts with category, total_amount, count, and relative_pct.
    """
    if not user_id:
        return []
    conn = get_db(db_path)
    try:
        cursor = conn.cursor()
        cursor.execute(
            """
            SELECT
                category,
                COUNT(*) AS count,
                COALESCE(SUM(amount), 0.0) AS total_amount
            FROM expenses
            WHERE user_id = ?
            GROUP BY category
            ORDER BY total_amount DESC;
            """,
            (user_id,),
        )
        rows = cursor.fetchall()
        if not rows:
            return []

        max_amount = max(float(r["total_amount"]) for r in rows) if rows else 0.0

        result = []
        for r in rows:
            amt = float(r["total_amount"])
            relative_pct = round((amt / max_amount * 100), 1) if max_amount > 0 else 0.0
            result.append({
                "category": r["category"],
                "total_amount": amt,
                "count": int(r["count"]),
                "relative_pct": relative_pct,
            })
        return result
    finally:
        conn.close()



