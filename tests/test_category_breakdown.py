import pytest
from database.db import init_db, create_user, get_db
from database.queries.breakdown import get_category_breakdown


@pytest.fixture
def temp_db(tmp_path):
    db_file = tmp_path / "test_breakdown.db"
    init_db(str(db_file))
    return str(db_file)


def test_category_breakdown_empty(temp_db):
    user = create_user("Zero", "zero@example.com", "pass123", db_path=temp_db)
    result = get_category_breakdown(user["id"], db_path=temp_db)
    assert result == []


def test_category_breakdown_none_user(temp_db):
    result = get_category_breakdown(None, db_path=temp_db)
    assert result == []


def test_category_breakdown_sums_to_100_percent(temp_db):
    user = create_user("Spender", "spender@example.com", "pass123", db_path=temp_db)
    conn = get_db(temp_db)
    try:
        with conn:
            # Three items with 10.0 each (1/3 each = 33.33% each -> normally rounds to 33, 33, 33 = 99%)
            # Our normalization must absorb the remainder so sum is strictly 100%
            conn.execute(
                """
                INSERT INTO expenses (user_id, amount, category, date, description)
                VALUES
                    (?, 10.0, 'Food', '2026-10-01', 'Item 1'),
                    (?, 10.0, 'Transport', '2026-10-02', 'Item 2'),
                    (?, 10.0, 'Bills', '2026-10-03', 'Item 3');
                """,
                (user["id"], user["id"], user["id"]),
            )
    finally:
        conn.close()

    breakdown = get_category_breakdown(user["id"], db_path=temp_db)
    assert len(breakdown) == 3
    # Check each item has required keys
    for item in breakdown:
        assert "name" in item
        assert "amount" in item
        assert "pct" in item
        assert isinstance(item["pct"], int)

    total_pct = sum(item["pct"] for item in breakdown)
    assert total_pct == 100


def test_category_breakdown_ordering(temp_db):
    user = create_user("Ordering User", "ordering@example.com", "pass123", db_path=temp_db)
    conn = get_db(temp_db)
    try:
        with conn:
            conn.execute(
                """
                INSERT INTO expenses (user_id, amount, category, date, description)
                VALUES
                    (?, 100.0, 'Other', '2026-10-01', 'Minor'),
                    (?, 1000.0, 'Bills', '2026-10-02', 'Major'),
                    (?, 500.0, 'Food', '2026-10-03', 'Medium');
                """,
                (user["id"], user["id"], user["id"]),
            )
    finally:
        conn.close()

    breakdown = get_category_breakdown(user["id"], db_path=temp_db)
    assert len(breakdown) == 3
    # Ordered descending by total amount
    assert breakdown[0]["name"] == "Bills"
    assert breakdown[0]["amount"] == 1000.0
    assert breakdown[1]["name"] == "Food"
    assert breakdown[1]["amount"] == 500.0
    assert breakdown[2]["name"] == "Other"
    assert breakdown[2]["amount"] == 100.0

    total_pct = sum(item["pct"] for item in breakdown)
    assert total_pct == 100


def test_category_breakdown_user_isolation(temp_db):
    u1 = create_user("U1", "u1@example.com", "pass123", db_path=temp_db)
    u2 = create_user("U2", "u2@example.com", "pass123", db_path=temp_db)

    conn = get_db(temp_db)
    try:
        with conn:
            conn.execute(
                """
                INSERT INTO expenses (user_id, amount, category, date, description)
                VALUES
                    (?, 200.0, 'Entertainment', '2026-10-01', 'U1 Fun'),
                    (?, 900.0, 'Shopping', '2026-10-02', 'U2 Clothes');
                """,
                (u1["id"], u2["id"]),
            )
    finally:
        conn.close()

    b1 = get_category_breakdown(u1["id"], db_path=temp_db)
    assert len(b1) == 1
    assert b1[0]["name"] == "Entertainment"
    assert b1[0]["pct"] == 100

    b2 = get_category_breakdown(u2["id"], db_path=temp_db)
    assert len(b2) == 1
    assert b2[0]["name"] == "Shopping"
    assert b2[0]["pct"] == 100
