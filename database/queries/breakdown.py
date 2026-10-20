"""
database/queries/breakdown.py
Category breakdown query helper for Spendly.
"""

from database.db import get_db


def get_category_breakdown(user_id, date_from=None, date_to=None, db_path=None):
    """
    Query spending grouped by category for a user, sorted descending by total amount.
    Optionally filters by date range (inclusive: date BETWEEN date_from AND date_to)
    when both date_from and date_to are provided.
    Returns a list of dicts:
        [
            {
                "name": str,
                "category": str,
                "amount": float,
                "total_amount": float,
                "pct": int,
                "relative_pct": int,
            },
            ...
        ]
    Percentages are integers that strictly sum to 100% across all categories (with rounding
    remainder absorbed into the largest category).
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
            "SELECT category, COALESCE(SUM(amount), 0.0) AS total "
            "FROM expenses WHERE user_id = ?" + date_clause + " "
            "GROUP BY category "
            "ORDER BY total DESC, category ASC;"
        )
        cursor.execute(sql, (user_id, *date_params))
        rows = cursor.fetchall()
        if not rows:
            return []

        total_spent = sum(float(r["total"]) for r in rows)
        if total_spent <= 0:
            return []

        # 1. Compute raw integer percentages
        raw_breakdown = []
        for r in rows:
            amt = float(r["total"])
            pct = int(round((amt / total_spent) * 100))
            raw_breakdown.append({
                "name": r["category"],
                "category": r["category"],
                "amount": amt,
                "total_amount": amt,
                "pct": pct,
                "relative_pct": pct,
            })

        # 2. Absorb rounding remainder into the highest category (first item)
        pct_sum = sum(item["pct"] for item in raw_breakdown)
        remainder = 100 - pct_sum
        if raw_breakdown and remainder != 0:
            raw_breakdown[0]["pct"] += remainder
            raw_breakdown[0]["relative_pct"] = raw_breakdown[0]["pct"]

        return raw_breakdown
    finally:
        conn.close()
