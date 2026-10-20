import pytest
from database.db import init_db, create_user, get_db
from database.queries.stats import get_user_by_id, get_summary_stats


@pytest.fixture
def temp_db(tmp_path):
    db_file = tmp_path / "test_stats.db"
    init_db(str(db_file))
    return str(db_file)


def test_get_user_by_id(temp_db):
    user = create_user("Rohan Varma", "rohan@example.com", "secure123", db_path=temp_db)
    fetched = get_user_by_id(user["id"], db_path=temp_db)
    assert fetched is not None
    assert fetched["id"] == user["id"]
    assert fetched["name"] == "Rohan Varma"
    assert fetched["email"] == "rohan@example.com"
    assert "member_since" in fetched
    # e.g., October 2026
    assert len(fetched["member_since"].split()) == 2

    # Non-existent user
    assert get_user_by_id(99999, db_path=temp_db) is None
    assert get_user_by_id(None, db_path=temp_db) is None


def test_get_summary_stats_zero_expenses(temp_db):
    user = create_user("Zero User", "zero@example.com", "secure123", db_path=temp_db)
    stats = get_summary_stats(user["id"], db_path=temp_db)
    assert stats["total_spent"] == 0.0
    assert stats["transaction_count"] == 0
    assert stats["top_category"] == "—"


def test_get_summary_stats_none_user(temp_db):
    stats = get_summary_stats(None, db_path=temp_db)
    assert stats["total_spent"] == 0.0
    assert stats["transaction_count"] == 0
    assert stats["top_category"] == "—"


def test_get_summary_stats_with_expenses(temp_db):
    user = create_user("Spender", "spender@example.com", "secure123", db_path=temp_db)
    conn = get_db(temp_db)
    try:
        with conn:
            conn.execute(
                """
                INSERT INTO expenses (user_id, amount, category, date, description)
                VALUES
                    (?, 150.0, 'Food', '2026-10-01', 'Breakfast'),
                    (?, 350.0, 'Food', '2026-10-02', 'Dinner'),
                    (?, 1200.0, 'Bills', '2026-10-05', 'Electricity'),
                    (?, 250.0, 'Transport', '2026-10-06', 'Cab');
                """,
                (user["id"], user["id"], user["id"], user["id"]),
            )
    finally:
        conn.close()

    stats = get_summary_stats(user["id"], db_path=temp_db)
    assert stats["transaction_count"] == 4
    assert stats["total_spent"] == 1950.0
    assert stats["top_category"] == "Bills"


def test_get_summary_stats_user_isolation(temp_db):
    u1 = create_user("U1", "u1@example.com", "pass12345", db_path=temp_db)
    u2 = create_user("U2", "u2@example.com", "pass12345", db_path=temp_db)

    conn = get_db(temp_db)
    try:
        with conn:
            conn.execute(
                """
                INSERT INTO expenses (user_id, amount, category, date, description)
                VALUES
                    (?, 200.0, 'Food', '2026-10-01', 'U1 Food'),
                    (?, 800.0, 'Bills', '2026-10-02', 'U2 Bills');
                """,
                (u1["id"], u2["id"]),
            )
    finally:
        conn.close()

    s1 = get_summary_stats(u1["id"], db_path=temp_db)
    assert s1["total_spent"] == 200.0
    assert s1["top_category"] == "Food"

    s2 = get_summary_stats(u2["id"], db_path=temp_db)
    assert s2["total_spent"] == 800.0
    assert s2["top_category"] == "Bills"
