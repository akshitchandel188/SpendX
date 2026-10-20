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
