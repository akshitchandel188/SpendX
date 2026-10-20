"""
database/queries.py
Pure query helpers for Spendly (re-exported from database.queries package).
"""

from database.queries.stats import get_user_by_id, get_summary_stats
from database.queries.transactions import get_recent_transactions, insert_expense
from database.queries.breakdown import get_category_breakdown

__all__ = [
    "get_user_by_id",
    "get_summary_stats",
    "get_recent_transactions",
    "get_category_breakdown",
    "insert_expense",
]
