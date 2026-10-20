import pytest
from database.db import init_db, create_user, get_db
from database.queries.transactions import get_recent_transactions


@pytest.fixture
def temp_db(tmp_path):
    db_file = tmp_path / "test_transactions.db"
    init_db(str(db_file))
    return str(db_file)


def test_recent_transactions_empty(temp_db):
    user = create_user("Alice", "alice@example.com", "password123", db_path=temp_db)
    result = get_recent_transactions(user["id"], db_path=temp_db)
    assert result == []


def test_recent_transactions_none_user(temp_db):
    result = get_recent_transactions(None, db_path=temp_db)
    assert result == []


def test_recent_transactions_ordering_and_limit(temp_db):
    user = create_user("Bob", "bob@example.com", "password123", db_path=temp_db)
    conn = get_db(temp_db)
    try:
        with conn:
            conn.execute(
                """
                INSERT INTO expenses (user_id, amount, category, date, description)
                VALUES
                    (?, 100.0, 'Food', '2026-10-01', 'Breakfast'),
                    (?, 200.0, 'Transport', '2026-10-05', 'Train ticket'),
                    (?, 300.0, 'Bills', '2026-10-10', 'Electricity'),
                    (?, 400.0, 'Shopping', '2026-10-15', 'Jacket');
                """,
                (user["id"], user["id"], user["id"], user["id"]),
            )
    finally:
        conn.close()

    # Query with default limit=10
    transactions = get_recent_transactions(user["id"], db_path=temp_db)
    assert len(transactions) == 4
    # Ordered newest first (date DESC, id DESC)
    assert transactions[0]["description"] == "Jacket"
    assert transactions[0]["amount"] == 400.0
    assert transactions[1]["description"] == "Electricity"
    assert transactions[2]["description"] == "Train ticket"
    assert transactions[3]["description"] == "Breakfast"

    # Query with limit=2
    limited = get_recent_transactions(user["id"], limit=2, db_path=temp_db)
    assert len(limited) == 2
    assert limited[0]["description"] == "Jacket"
    assert limited[1]["description"] == "Electricity"


def test_recent_transactions_user_isolation(temp_db):
    user1 = create_user("User1", "user1@example.com", "pass12345", db_path=temp_db)
    user2 = create_user("User2", "user2@example.com", "pass12345", db_path=temp_db)

    conn = get_db(temp_db)
    try:
        with conn:
            conn.execute(
                """
                INSERT INTO expenses (user_id, amount, category, date, description)
                VALUES
                    (?, 150.0, 'Food', '2026-10-02', 'User1 Lunch'),
                    (?, 500.0, 'Bills', '2026-10-03', 'User2 Rent');
                """,
                (user1["id"], user2["id"]),
            )
    finally:
        conn.close()

    res1 = get_recent_transactions(user1["id"], db_path=temp_db)
    assert len(res1) == 1
    assert res1[0]["description"] == "User1 Lunch"
    assert res1[0]["amount"] == 150.0

    res2 = get_recent_transactions(user2["id"], db_path=temp_db)
    assert len(res2) == 1
    assert res2[0]["description"] == "User2 Rent"
    assert res2[0]["amount"] == 500.0
