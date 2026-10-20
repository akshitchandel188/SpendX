"""
database/queries/transactions.py
Transaction history query helper for Spendly.
"""

from database.db import get_db


def get_recent_transactions(user_id, limit=10, db_path=None):
    """
    Fetch recent transactions for a user, ordered newest first (date DESC, id DESC).
    Returns a list of dicts:
        [{"id": int, "amount": float, "category": str, "date": str, "description": str}, ...]
    Returns an empty list if user_id is missing or if user has no expenses.
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
