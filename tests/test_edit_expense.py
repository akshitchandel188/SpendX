import pytest
from app import app
from database.db import init_db, create_user, get_db, CATEGORIES
from database.queries import (
    insert_expense,
    get_expense_by_id,
    update_expense,
)


@pytest.fixture
def test_client(tmp_path):
    """Provides an isolated Flask test client with a clean temporary SQLite database."""
    db_file = tmp_path / "test_spendly_edit.db"
    init_db(str(db_file))
    app.config.update({
        "TESTING": True,
        "DATABASE": str(db_file),
        "SECRET_KEY": "test-edit-expense-secret-key",
    })
    with app.test_client() as client:
        yield client, str(db_file)


# ---------------------------------------------------------------------------
# Unit tests for get_expense_by_id and update_expense
# ---------------------------------------------------------------------------


def test_get_expense_by_id_success(test_client):
    """get_expense_by_id retrieves the correct expense record."""
    _, db_path = test_client
    user = create_user("Alice", "alice@example.com", "password123", db_path=db_path)
    exp_id = insert_expense(
        user_id=user["id"],
        amount=45.50,
        category="Food",
        date="2026-03-15",
        description="Grocery run",
        db_path=db_path,
    )

    # Without user_id check
    expense = get_expense_by_id(exp_id, db_path=db_path)
    assert expense is not None
    assert expense["id"] == exp_id
    assert expense["user_id"] == user["id"]
    assert expense["amount"] == 45.50
    assert expense["category"] == "Food"
    assert expense["date"] == "2026-03-15"
    assert expense["description"] == "Grocery run"

    # With matching user_id check
    expense_with_user = get_expense_by_id(exp_id, user_id=user["id"], db_path=db_path)
    assert expense_with_user is not None
    assert expense_with_user["id"] == exp_id


def test_get_expense_by_id_mismatched_user_or_not_found(test_client):
    """get_expense_by_id returns None when user_id does not match or ID does not exist."""
    _, db_path = test_client
    user1 = create_user("User 1", "u1@example.com", "password123", db_path=db_path)
    user2 = create_user("User 2", "u2@example.com", "password123", db_path=db_path)

    exp_id = insert_expense(
        user_id=user1["id"],
        amount=10.0,
        category="Transport",
        date="2026-03-10",
        description="Bus",
        db_path=db_path,
    )

    # Other user should get None
    assert get_expense_by_id(exp_id, user_id=user2["id"], db_path=db_path) is None
    # Non-existent ID
    assert get_expense_by_id(99999, user_id=user1["id"], db_path=db_path) is None
    assert get_expense_by_id(None, db_path=db_path) is None


def test_update_expense_success(test_client):
    """update_expense updates fields and persists to SQLite."""
    _, db_path = test_client
    user = create_user("Bob", "bob@example.com", "password123", db_path=db_path)
    exp_id = insert_expense(
        user_id=user["id"],
        amount=25.0,
        category="Bills",
        date="2026-03-01",
        description="Water bill",
        db_path=db_path,
    )

    success = update_expense(
        expense_id=exp_id,
        user_id=user["id"],
        amount=32.75,
        category="Health",
        date="2026-03-05",
        description="Medicine",
        db_path=db_path,
    )
    assert success is True

    updated = get_expense_by_id(exp_id, user_id=user["id"], db_path=db_path)
    assert updated["amount"] == 32.75
    assert updated["category"] == "Health"
    assert updated["date"] == "2026-03-05"
    assert updated["description"] == "Medicine"


def test_update_expense_empty_description_stored_as_null(test_client):
    """update_expense with blank/whitespace description stores NULL."""
    _, db_path = test_client
    user = create_user("Charlie", "charlie@example.com", "password123", db_path=db_path)
    exp_id = insert_expense(
        user_id=user["id"],
        amount=100.0,
        category="Shopping",
        date="2026-03-01",
        description="Initial description",
        db_path=db_path,
    )

    success = update_expense(
        expense_id=exp_id,
        user_id=user["id"],
        amount=100.0,
        category="Shopping",
        date="2026-03-01",
        description="   ",
        db_path=db_path,
    )
    assert success is True

    conn = get_db(db_path)
    try:
        cursor = conn.cursor()
        cursor.execute("SELECT description FROM expenses WHERE id = ?", (exp_id,))
        row = cursor.fetchone()
        assert row["description"] is None
    finally:
        conn.close()


def test_update_expense_unauthorized_or_missing(test_client):
    """update_expense returns False when user is not owner or expense ID does not exist."""
    _, db_path = test_client
    user1 = create_user("U1", "user1@example.com", "password123", db_path=db_path)
    user2 = create_user("U2", "user2@example.com", "password123", db_path=db_path)
    exp_id = insert_expense(
        user_id=user1["id"],
        amount=50.0,
        category="Food",
        date="2026-03-01",
        description="Dinner",
        db_path=db_path,
    )

    # User 2 tries to update User 1's expense
    updated = update_expense(
        expense_id=exp_id,
        user_id=user2["id"],
        amount=99.0,
        category="Other",
        date="2026-03-02",
        description="Hacked",
        db_path=db_path,
    )
    assert updated is False

    # Original expense remains untouched
    original = get_expense_by_id(exp_id, user_id=user1["id"], db_path=db_path)
    assert original["amount"] == 50.0
    assert original["category"] == "Food"

    # Non-existent ID returns False
    assert update_expense(99999, user1["id"], 10.0, "Food", "2026-03-01", db_path=db_path) is False


# ---------------------------------------------------------------------------
# Route tests: Authentication & Authorization
# ---------------------------------------------------------------------------


def test_edit_expense_unauthenticated_redirects_login(test_client):
    """GET and POST /expenses/<id>/edit redirect to /login when unauthenticated."""
    client, _ = test_client

    get_resp = client.get("/expenses/1/edit")
    assert get_resp.status_code == 302
    assert "/login" in get_resp.headers["Location"]

    post_resp = client.post("/expenses/1/edit", data={"amount": "20.00", "category": "Food", "date": "2026-03-01"})
    assert post_resp.status_code == 302
    assert "/login" in post_resp.headers["Location"]


def test_edit_expense_not_found_returns_404(test_client):
    """GET and POST for a non-existent expense return 404."""
    client, db_path = test_client
    user = create_user("Test User", "testuser@example.com", "password123", db_path=db_path)

    with client.session_transaction() as sess:
        sess["user_id"] = user["id"]
        sess["user_name"] = user["name"]

    get_resp = client.get("/expenses/99999/edit")
    assert get_resp.status_code == 404

    post_resp = client.post(
        "/expenses/99999/edit",
        data={"amount": "50.00", "category": "Food", "date": "2026-03-01"},
    )
    assert post_resp.status_code == 404


def test_edit_expense_other_user_expense_returns_404(test_client):
    """GET and POST for an expense belonging to a different user return 404."""
    client, db_path = test_client
    owner = create_user("Owner", "owner@example.com", "password123", db_path=db_path)
    other = create_user("Other", "other@example.com", "password123", db_path=db_path)

    exp_id = insert_expense(
        user_id=owner["id"],
        amount=75.0,
        category="Entertainment",
        date="2026-03-12",
        description="Concert",
        db_path=db_path,
    )

    # Log in as other user
    with client.session_transaction() as sess:
        sess["user_id"] = other["id"]
        sess["user_name"] = other["name"]

    get_resp = client.get(f"/expenses/{exp_id}/edit")
    assert get_resp.status_code == 404

    post_resp = client.post(
        f"/expenses/{exp_id}/edit",
        data={"amount": "10.00", "category": "Food", "date": "2026-03-12"},
    )
    assert post_resp.status_code == 404


# ---------------------------------------------------------------------------
# Route tests: GET form rendering
# ---------------------------------------------------------------------------


def test_edit_expense_get_form_rendering(test_client):
    """GET /expenses/<id>/edit renders form pre-populated with existing expense data."""
    client, db_path = test_client
    user = create_user("Dave", "dave@example.com", "password123", db_path=db_path)
    exp_id = insert_expense(
        user_id=user["id"],
        amount=89.99,
        category="Shopping",
        date="2026-03-18",
        description="New headphones",
        db_path=db_path,
    )

    with client.session_transaction() as sess:
        sess["user_id"] = user["id"]
        sess["user_name"] = user["name"]

    resp = client.get(f"/expenses/{exp_id}/edit")
    assert resp.status_code == 200
    html = resp.data.decode("utf-8")

    assert "Edit Expense" in html
    assert 'value="89.99"' in html
    assert 'value="2026-03-18"' in html
    assert 'value="New headphones"' in html
    assert f'action="/expenses/{exp_id}/edit"' in html
    assert 'href="/profile"' in html

    for cat in CATEGORIES:
        assert cat in html

    assert 'value="Shopping" selected' in html


# ---------------------------------------------------------------------------
# Route tests: POST validation and updates
# ---------------------------------------------------------------------------


def test_edit_expense_post_valid_data(test_client):
    """POST /expenses/<id>/edit with valid data updates expense and redirects to /profile."""
    client, db_path = test_client
    user = create_user("Eve", "eve@example.com", "password123", db_path=db_path)
    exp_id = insert_expense(
        user_id=user["id"],
        amount=40.0,
        category="Food",
        date="2026-03-10",
        description="Old Lunch",
        db_path=db_path,
    )

    with client.session_transaction() as sess:
        sess["user_id"] = user["id"]
        sess["user_name"] = user["name"]

    resp = client.post(
        f"/expenses/{exp_id}/edit",
        data={
            "amount": "65.50",
            "category": "Bills",
            "date": "2026-03-15",
            "description": "Electricity",
        },
    )
    assert resp.status_code == 302
    assert resp.headers["Location"].endswith("/profile")

    updated = get_expense_by_id(exp_id, user_id=user["id"], db_path=db_path)
    assert updated["amount"] == 65.50
    assert updated["category"] == "Bills"
    assert updated["date"] == "2026-03-15"
    assert updated["description"] == "Electricity"


def test_edit_expense_post_missing_amount(test_client):
    """POST with missing amount re-renders form with error and preserved inputs."""
    client, db_path = test_client
    user = create_user("Frank", "frank@example.com", "password123", db_path=db_path)
    exp_id = insert_expense(
        user_id=user["id"],
        amount=50.0,
        category="Health",
        date="2026-03-10",
        description="Checkup",
        db_path=db_path,
    )

    with client.session_transaction() as sess:
        sess["user_id"] = user["id"]
        sess["user_name"] = user["name"]

    resp = client.post(
        f"/expenses/{exp_id}/edit",
        data={
            "amount": "",
            "category": "Health",
            "date": "2026-03-11",
            "description": "Dental checkup",
        },
    )
    assert resp.status_code == 200
    html = resp.data.decode("utf-8")
    assert "Please enter an amount." in html
    assert 'value="Dental checkup"' in html


def test_edit_expense_post_invalid_amount_zero_or_negative(test_client):
    """POST with amount <= 0 re-renders form with error."""
    client, db_path = test_client
    user = create_user("Grace", "grace@example.com", "password123", db_path=db_path)
    exp_id = insert_expense(
        user_id=user["id"],
        amount=50.0,
        category="Food",
        date="2026-03-10",
        description="Snack",
        db_path=db_path,
    )

    with client.session_transaction() as sess:
        sess["user_id"] = user["id"]
        sess["user_name"] = user["name"]

    for bad_amt in ["0", "-5.50"]:
        resp = client.post(
            f"/expenses/{exp_id}/edit",
            data={
                "amount": bad_amt,
                "category": "Food",
                "date": "2026-03-10",
                "description": "Snack",
            },
        )
        assert resp.status_code == 200
        html = resp.data.decode("utf-8")
        assert "Amount must be greater than zero." in html


def test_edit_expense_post_non_numeric_amount(test_client):
    """POST with non-numeric amount re-renders form with error."""
    client, db_path = test_client
    user = create_user("Heidi", "heidi@example.com", "password123", db_path=db_path)
    exp_id = insert_expense(
        user_id=user["id"],
        amount=50.0,
        category="Food",
        date="2026-03-10",
        description="Snack",
        db_path=db_path,
    )

    with client.session_transaction() as sess:
        sess["user_id"] = user["id"]
        sess["user_name"] = user["name"]

    resp = client.post(
        f"/expenses/{exp_id}/edit",
        data={
            "amount": "abc",
            "category": "Food",
            "date": "2026-03-10",
            "description": "Snack",
        },
    )
    assert resp.status_code == 200
    html = resp.data.decode("utf-8")
    assert "Amount must be a valid number." in html


def test_edit_expense_post_invalid_category(test_client):
    """POST with invalid category re-renders form with error."""
    client, db_path = test_client
    user = create_user("Ivan", "ivan@example.com", "password123", db_path=db_path)
    exp_id = insert_expense(
        user_id=user["id"],
        amount=50.0,
        category="Food",
        date="2026-03-10",
        description="Snack",
        db_path=db_path,
    )

    with client.session_transaction() as sess:
        sess["user_id"] = user["id"]
        sess["user_name"] = user["name"]

    resp = client.post(
        f"/expenses/{exp_id}/edit",
        data={
            "amount": "50.00",
            "category": "Cryptocurrency",
            "date": "2026-03-10",
            "description": "Snack",
        },
    )
    assert resp.status_code == 200
    html = resp.data.decode("utf-8")
    assert "Please select a valid category." in html


def test_edit_expense_post_invalid_date(test_client):
    """POST with invalid date format re-renders form with error."""
    client, db_path = test_client
    user = create_user("Judy", "judy@example.com", "password123", db_path=db_path)
    exp_id = insert_expense(
        user_id=user["id"],
        amount=50.0,
        category="Food",
        date="2026-03-10",
        description="Snack",
        db_path=db_path,
    )

    with client.session_transaction() as sess:
        sess["user_id"] = user["id"]
        sess["user_name"] = user["name"]

    resp = client.post(
        f"/expenses/{exp_id}/edit",
        data={
            "amount": "50.00",
            "category": "Food",
            "date": "10-03-2026",
            "description": "Snack",
        },
    )
    assert resp.status_code == 200
    html = resp.data.decode("utf-8")
    assert "Date must be a valid date in YYYY-MM-DD format." in html


def test_edit_expense_post_description_too_long(test_client):
    """POST with description > 200 characters re-renders form with error."""
    client, db_path = test_client
    user = create_user("Kevin", "kevin@example.com", "password123", db_path=db_path)
    exp_id = insert_expense(
        user_id=user["id"],
        amount=50.0,
        category="Food",
        date="2026-03-10",
        description="Snack",
        db_path=db_path,
    )

    with client.session_transaction() as sess:
        sess["user_id"] = user["id"]
        sess["user_name"] = user["name"]

    resp = client.post(
        f"/expenses/{exp_id}/edit",
        data={
            "amount": "50.00",
            "category": "Food",
            "date": "2026-03-10",
            "description": "A" * 201,
        },
    )
    assert resp.status_code == 200
    html = resp.data.decode("utf-8")
    assert "Description cannot exceed 200 characters." in html


def test_edit_expense_post_empty_description_saves_null(test_client):
    """POST with empty description updates record and saves NULL description in DB."""
    client, db_path = test_client
    user = create_user("Laura", "laura@example.com", "password123", db_path=db_path)
    exp_id = insert_expense(
        user_id=user["id"],
        amount=50.0,
        category="Food",
        date="2026-03-10",
        description="Initial note",
        db_path=db_path,
    )

    with client.session_transaction() as sess:
        sess["user_id"] = user["id"]
        sess["user_name"] = user["name"]

    resp = client.post(
        f"/expenses/{exp_id}/edit",
        data={
            "amount": "55.00",
            "category": "Food",
            "date": "2026-03-11",
            "description": "",
        },
    )
    assert resp.status_code == 302
    assert resp.headers["Location"].endswith("/profile")

    conn = get_db(db_path)
    try:
        cursor = conn.cursor()
        cursor.execute("SELECT description, amount FROM expenses WHERE id = ?", (exp_id,))
        row = cursor.fetchone()
        assert row["amount"] == 55.00
        assert row["description"] is None
    finally:
        conn.close()


# ---------------------------------------------------------------------------
# UI / Navigation Integration Test
# ---------------------------------------------------------------------------


def test_profile_recent_transactions_has_edit_link(test_client):
    """The recent transactions table on /profile displays an Edit link pointing to /expenses/<id>/edit."""
    client, db_path = test_client
    user = create_user("Mallory", "mallory@example.com", "password123", db_path=db_path)
    exp_id = insert_expense(
        user_id=user["id"],
        amount=19.99,
        category="Transport",
        date="2026-03-14",
        description="Subway fare",
        db_path=db_path,
    )

    with client.session_transaction() as sess:
        sess["user_id"] = user["id"]
        sess["user_name"] = user["name"]

    resp = client.get("/profile")
    assert resp.status_code == 200
    html = resp.data.decode("utf-8")

    assert "ACTIONS" in html
    assert f'href="/expenses/{exp_id}/edit"' in html
    assert "Edit" in html
