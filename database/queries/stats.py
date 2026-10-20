"""
database/queries/stats.py
Summary statistics and user profile query helpers for Spendly.
"""

from datetime import datetime
from database.db import get_db


def _format_member_since(raw_date):
    if not raw_date:
        return "N/A"
    try:
        dt = datetime.strptime(str(raw_date)[:19], "%Y-%m-%d %H:%M:%S")
        return dt.strftime("%B %Y")
    except Exception:
        try:
            dt = datetime.strptime(str(raw_date)[:10], "%Y-%m-%d")
            return dt.strftime("%B %Y")
        except Exception:
            return str(raw_date)


def get_user_by_id(user_id, db_path=None):
    """
    Look up user by primary key ID and return user dict with formatted member_since ("Month YYYY").
    Returns None if user is not found or user_id is falsy.
    """
    if not user_id:
        return None

    conn = get_db(db_path)
    try:
        cursor = conn.cursor()
        cursor.execute(
            "SELECT id, name, email, created_at FROM users WHERE id = ?;",
            (user_id,),
        )
        row = cursor.fetchone()
        if not row:
            return None

        return {
            "id": int(row["id"]),
            "name": row["name"],
            "email": row["email"],
            "member_since": _format_member_since(row["created_at"]),
            "created_at": row["created_at"],
        }
    finally:
        conn.close()


def get_summary_stats(user_id, date_from=None, date_to=None, db_path=None):
    """
    Query total spending amount, transaction count, and top category for a user.
    Optionally filters by date range (inclusive: date BETWEEN date_from AND date_to)
    when both date_from and date_to are provided.
    Returns:
        {
            "total_spent": float,
            "total_amount": float,
            "transaction_count": int,
            "total_count": int,
            "top_category": str,
        }
    For users with no expenses, returns zeros and "—" for top_category.
    """
    default_stats = {
        "total_spent": 0.0,
        "total_amount": 0.0,
        "transaction_count": 0,
        "total_count": 0,
        "top_category": "—",
    }
    if not user_id:
        return default_stats

    conn = get_db(db_path)
    try:
        cursor = conn.cursor()
        has_date_filter = bool(date_from and date_to)
        date_clause = " AND date BETWEEN ? AND ?" if has_date_filter else ""
        date_params = (date_from, date_to) if has_date_filter else ()

        # 1. Total count & total amount
        count_sql = (
            "SELECT COUNT(*) AS count, COALESCE(SUM(amount), 0.0) AS total "
            "FROM expenses WHERE user_id = ?" + date_clause + ";"
        )
        cursor.execute(count_sql, (user_id, *date_params))
        agg = cursor.fetchone()
        count = int(agg["count"]) if agg else 0
        total = float(agg["total"]) if agg else 0.0

        if count == 0:
            return default_stats

        # 2. Top category by total spend
        top_cat_sql = (
            "SELECT category, SUM(amount) AS cat_total "
            "FROM expenses WHERE user_id = ?" + date_clause + " "
            "GROUP BY category "
            "ORDER BY cat_total DESC, category ASC "
            "LIMIT 1;"
        )
        cursor.execute(top_cat_sql, (user_id, *date_params))
        top_row = cursor.fetchone()
        top_cat = top_row["category"] if top_row else "—"

        return {
            "total_spent": total,
            "total_amount": total,
            "transaction_count": count,
            "total_count": count,
            "top_category": top_cat,
        }
    finally:
        conn.close()
