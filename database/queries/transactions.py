"""
database/queries/transactions.py
Transaction history query helper for Spendly.
"""

from database.db import get_db


def get_recent_transactions(user_id, limit=10, date_from=None, date_to=None, db_path=None):
    """
    Fetch recent transactions for a user, ordered newest first (date DESC, id DESC).
    Optionally filters by date range (inclusive: date BETWEEN date_from AND date_to)
    when both date_from and date_to are provided.
    Returns a list of dicts:
        [{"id": int, "amount": float, "category": str, "date": str, "description": str}, ...]
    Returns an empty list if user_id is missing or if user has no expenses.
    """
    if not user_id:
        return []

    conn = get_db(db_path)
    try:
        cursor = conn.cursor()
        has_date_filter = bool(date_from and date_to)
        date_clause = " AND date BETWEEN ? AND ?" if has_date_filter else ""
        date_params = (date_from, date_to) if has_date_filter else ()

        sql = (
            "SELECT id, amount, category, date, description "
            "FROM expenses WHERE user_id = ?" + date_clause + " "
            "ORDER BY date DESC, id DESC LIMIT ?;"
        )
        cursor.execute(sql, (user_id, *date_params, limit))
        rows = cursor.fetchall()
        return [
            {
                "id": row["id"],
                "amount": float(row["amount"]),
                "category": row["category"],
                "date": row["date"],
                "description": row["description"] or "",
            }
            for row in rows
        ]
    finally:
        conn.close()


def insert_expense(user_id, amount, category, date, description=None, db_path=None):
    """
    Insert a new expense into the expenses table.
    description is optional; blank or whitespace-only strings are stored as None (NULL).
    Returns the newly inserted expense row ID.
    """
    if description is not None:
        description = description.strip()
        if not description:
            description = None

    conn = get_db(db_path)
    try:
        with conn:
            cursor = conn.cursor()
            cursor.execute(
                """
                INSERT INTO expenses (user_id, amount, category, date, description)
                VALUES (?, ?, ?, ?, ?);
                """,
                (user_id, float(amount), category, str(date), description),
            )
            return cursor.lastrowid
    finally:
        conn.close()


def get_expense_by_id(expense_id, user_id=None, db_path=None):
    """
    Fetch a single expense by ID, optionally verifying ownership by user_id.
    Returns a dict of expense fields or None if not found.
    """
    if not expense_id:
        return None

    conn = get_db(db_path)
    try:
        cursor = conn.cursor()
        if user_id is not None:
            cursor.execute(
                "SELECT id, user_id, amount, category, date, description, created_at "
                "FROM expenses WHERE id = ? AND user_id = ?;",
                (expense_id, user_id),
            )
        else:
            cursor.execute(
                "SELECT id, user_id, amount, category, date, description, created_at "
                "FROM expenses WHERE id = ?;",
                (expense_id,),
            )
        row = cursor.fetchone()
        if not row:
            return None
        return {
            "id": row["id"],
            "user_id": row["user_id"],
            "amount": float(row["amount"]),
            "category": row["category"],
            "date": row["date"],
            "description": row["description"] or "",
            "created_at": row["created_at"],
        }
    finally:
        conn.close()


def update_expense(expense_id, user_id, amount, category, date, description=None, db_path=None):
    """
    Update an existing expense record matching expense_id and user_id.
    description is optional; blank or whitespace-only strings are stored as None (NULL).
    Returns True if a row was updated, False otherwise.
    """
    if not expense_id or not user_id:
        return False

    if description is not None:
        description = description.strip()
        if not description:
            description = None

    conn = get_db(db_path)
    try:
        with conn:
            cursor = conn.cursor()
            cursor.execute(
                """
                UPDATE expenses
                SET amount = ?, category = ?, date = ?, description = ?
                WHERE id = ? AND user_id = ?;
                """,
                (float(amount), category, str(date), description, expense_id, user_id),
            )
            return cursor.rowcount > 0
    finally:
        conn.close()


