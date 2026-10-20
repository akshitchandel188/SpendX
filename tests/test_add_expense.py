import pytest
from app import app
from database.db import init_db, create_user, get_db, CATEGORIES
from database.queries import insert_expense


@pytest.fixture
def test_client(tmp_path):
    """Provides an isolated Flask test client with a clean temporary SQLite database."""
    db_file = tmp_path / "test_spendly.db"
    init_db(str(db_file))
    app.config.update({
        "TESTING": True,
        "DATABASE": str(db_file),
        "SECRET_KEY": "test-add-expense-secret-key",
    })
    with app.test_client() as client:
        yield client, str(db_file)


# ---------------------------------------------------------------------------
# Unit tests for insert_expense
# ---------------------------------------------------------------------------


def test_insert_expense_valid_data(test_client):
    """insert_expense should insert row and querying DB returns the new row."""
    _, db_path = test_client
    user = create_user("Test User", "test@example.com", "pass12345", db_path=db_path)

    new_id = insert_expense(
        user_id=user["id"],
        amount=50.0,
        category="Food",
        date="2026-03-20",
        description="Lunch",
        db_path=db_path,
    )
    assert new_id is not None
    assert isinstance(new_id, int)

    conn = get_db(db_path)
    try:
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM expenses WHERE id = ?", (new_id,))
        row = cursor.fetchone()
        assert row is not None
        assert row["user_id"] == user["id"]
        assert row["amount"] == 50.0
        assert row["category"] == "Food"
        assert row["date"] == "2026-03-20"
        assert row["description"] == "Lunch"
    finally:
        conn.close()


def test_insert_expense_none_description(test_client):
    """insert_expense with description=None stores description as NULL."""
    _, db_path = test_client
    user = create_user("Test User 2", "test2@example.com", "pass12345", db_path=db_path)

    new_id = insert_expense(
        user_id=user["id"],
        amount=120.5,
        category="Transport",
        date="2026-03-21",
        description=None,
        db_path=db_path,
    )

    conn = get_db(db_path)
    try:
        cursor = conn.cursor()
        cursor.execute("SELECT description FROM expenses WHERE id = ?", (new_id,))
        row = cursor.fetchone()
        assert row is not None
        assert row["description"] is None
    finally:
        conn.close()


def test_insert_expense_blank_whitespace_description_stored_as_null(test_client):
    """insert_expense with blank/whitespace description stores NULL."""
    _, db_path = test_client
    user = create_user("Test User 3", "test3@example.com", "pass12345", db_path=db_path)

    new_id = insert_expense(
        user_id=user["id"],
        amount=30.0,
        category="Bills",
        date="2026-03-22",
        description="   ",
        db_path=db_path,
    )

    conn = get_db(db_path)
    try:
        cursor = conn.cursor()
        cursor.execute("SELECT description FROM expenses WHERE id = ?", (new_id,))
        row = cursor.fetchone()
        assert row is not None
        assert row["description"] is None
    finally:
        conn.close()


# ---------------------------------------------------------------------------
# Route tests: GET /expenses/add
# ---------------------------------------------------------------------------


def test_add_expense_get_unauthenticated(test_client):
    """GET /expenses/add while logged out should redirect to /login."""
    client, _ = test_client
    response = client.get("/expenses/add")
    assert response.status_code == 302
    assert response.headers["Location"].endswith("/login")


def test_add_expense_get_authenticated(test_client):
    """GET /expenses/add while logged in returns 200, form, and all 7 categories."""
    client, db_path = test_client
    user = create_user("Dev User", "dev@example.com", "pass12345", db_path=db_path)

    with client.session_transaction() as sess:
        sess["user_id"] = user["id"]
        sess["user_name"] = user["name"]

    response = client.get("/expenses/add")
    assert response.status_code == 200
    html = response.get_data(as_text=True)

    assert "<form" in html
    assert 'method="POST"' in html or 'method="post"' in html
    assert 'name="amount"' in html
    assert 'name="category"' in html
    assert 'name="date"' in html
    assert 'name="description"' in html

    for cat in CATEGORIES:
        assert f'<option value="{cat}"' in html


# ---------------------------------------------------------------------------
# Route tests: POST /expenses/add
# ---------------------------------------------------------------------------


def test_add_expense_post_unauthenticated(test_client):
    """POST /expenses/add while logged out should redirect to /login."""
    client, _ = test_client
    response = client.post(
        "/expenses/add",
        data={
            "amount": "50.0",
            "category": "Food",
            "date": "2026-03-20",
            "description": "Lunch",
        },
    )
    assert response.status_code == 302
    assert response.headers["Location"].endswith("/login")


def test_add_expense_post_success(test_client):
    """POST /expenses/add with valid data redirects to /profile and persists row."""
    client, db_path = test_client
    user = create_user("Valid User", "valid@example.com", "pass12345", db_path=db_path)

    with client.session_transaction() as sess:
        sess["user_id"] = user["id"]
        sess["user_name"] = user["name"]

    response = client.post(
        "/expenses/add",
        data={
            "amount": "50.0",
            "category": "Food",
            "date": "2026-03-20",
            "description": "Lunch with team",
        },
    )
    assert response.status_code == 302
    assert response.headers["Location"].endswith("/profile")

    # Verify expense in DB
    conn = get_db(db_path)
    try:
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM expenses WHERE user_id = ?", (user["id"],))
        rows = cursor.fetchall()
        assert len(rows) == 1
        assert rows[0]["amount"] == 50.0
        assert rows[0]["category"] == "Food"
        assert rows[0]["date"] == "2026-03-20"
        assert rows[0]["description"] == "Lunch with team"
    finally:
        conn.close()

    # Following redirect to profile shows new transaction
    follow_resp = client.get("/profile")
    assert follow_resp.status_code == 200
    follow_html = follow_resp.get_data(as_text=True)
    assert "Lunch with team" in follow_html
    assert "Food" in follow_html


def test_add_expense_post_success_no_description(test_client):
    """POST /expenses/add without description redirects to /profile and stores NULL."""
    client, db_path = test_client
    user = create_user("No Desc User", "nodesc@example.com", "pass12345", db_path=db_path)

    with client.session_transaction() as sess:
        sess["user_id"] = user["id"]
        sess["user_name"] = user["name"]

    response = client.post(
        "/expenses/add",
        data={
            "amount": "75.50",
            "category": "Shopping",
            "date": "2026-03-21",
            "description": "",
        },
    )
    assert response.status_code == 302
    assert response.headers["Location"].endswith("/profile")

    conn = get_db(db_path)
    try:
        cursor = conn.cursor()
        cursor.execute("SELECT description FROM expenses WHERE user_id = ?", (user["id"],))
        row = cursor.fetchone()
        assert row is not None
        assert row["description"] is None
    finally:
        conn.close()


def test_add_expense_post_missing_amount(test_client):
    """POST /expenses/add with missing amount returns 200 with error."""
    client, db_path = test_client
    user = create_user("Err User 1", "err1@example.com", "pass12345", db_path=db_path)

    with client.session_transaction() as sess:
        sess["user_id"] = user["id"]
        sess["user_name"] = user["name"]

    response = client.post(
        "/expenses/add",
        data={
            "amount": "",
            "category": "Food",
            "date": "2026-03-20",
            "description": "Lunch",
        },
    )
    assert response.status_code == 200
    html = response.get_data(as_text=True)
    assert "Please enter an amount" in html or "amount" in html.lower()
    assert 'value="Lunch"' in html


def test_add_expense_post_zero_amount(test_client):
    """POST /expenses/add with amount=0 returns 200 with error."""
    client, db_path = test_client
    user = create_user("Err User 2", "err2@example.com", "pass12345", db_path=db_path)

    with client.session_transaction() as sess:
        sess["user_id"] = user["id"]
        sess["user_name"] = user["name"]

    response = client.post(
        "/expenses/add",
        data={
            "amount": "0",
            "category": "Bills",
            "date": "2026-03-20",
            "description": "Zero bill",
        },
    )
    assert response.status_code == 200
    html = response.get_data(as_text=True)
    assert "greater than zero" in html or "error" in html.lower()
    assert 'value="0"' in html


def test_add_expense_post_negative_amount(test_client):
    """POST /expenses/add with negative amount returns 200 with error."""
    client, db_path = test_client
    user = create_user("Err User 3", "err3@example.com", "pass12345", db_path=db_path)

    with client.session_transaction() as sess:
        sess["user_id"] = user["id"]
        sess["user_name"] = user["name"]

    response = client.post(
        "/expenses/add",
        data={
            "amount": "-25.0",
            "category": "Food",
            "date": "2026-03-20",
            "description": "Negative",
        },
    )
    assert response.status_code == 200
    html = response.get_data(as_text=True)
    assert "greater than zero" in html or "error" in html.lower()


def test_add_expense_post_non_numeric_amount(test_client):
    """POST /expenses/add with non-numeric amount returns 200 with error."""
    client, db_path = test_client
    user = create_user("Err User 4", "err4@example.com", "pass12345", db_path=db_path)

    with client.session_transaction() as sess:
        sess["user_id"] = user["id"]
        sess["user_name"] = user["name"]

    response = client.post(
        "/expenses/add",
        data={
            "amount": "abc",
            "category": "Food",
            "date": "2026-03-20",
            "description": "Invalid amount",
        },
    )
    assert response.status_code == 200
    html = response.get_data(as_text=True)
    assert "valid number" in html or "error" in html.lower()
    assert 'value="abc"' in html


def test_add_expense_post_invalid_category(test_client):
    """POST /expenses/add with category not in list returns 200 with error."""
    client, db_path = test_client
    user = create_user("Err User 5", "err5@example.com", "pass12345", db_path=db_path)

    with client.session_transaction() as sess:
        sess["user_id"] = user["id"]
        sess["user_name"] = user["name"]

    response = client.post(
        "/expenses/add",
        data={
            "amount": "50.0",
            "category": "Luxury",
            "date": "2026-03-20",
            "description": "Invalid cat",
        },
    )
    assert response.status_code == 200
    html = response.get_data(as_text=True)
    assert "category" in html.lower()
    assert "valid" in html.lower()


def test_add_expense_post_invalid_date(test_client):
    """POST /expenses/add with invalid date string returns 200 with error."""
    client, db_path = test_client
    user = create_user("Err User 6", "err6@example.com", "pass12345", db_path=db_path)

    with client.session_transaction() as sess:
        sess["user_id"] = user["id"]
        sess["user_name"] = user["name"]

    response = client.post(
        "/expenses/add",
        data={
            "amount": "50.0",
            "category": "Food",
            "date": "20-03-2026",
            "description": "Wrong date format",
        },
    )
    assert response.status_code == 200
    html = response.get_data(as_text=True)
    assert "date" in html.lower()
    assert 'value="20-03-2026"' in html


def test_add_expense_post_description_too_long(test_client):
    """POST /expenses/add with description > 200 chars returns 200 with error."""
    client, db_path = test_client
    user = create_user("Err User 7", "err7@example.com", "pass12345", db_path=db_path)

    with client.session_transaction() as sess:
        sess["user_id"] = user["id"]
        sess["user_name"] = user["name"]

    long_desc = "x" * 205
    response = client.post(
        "/expenses/add",
        data={
            "amount": "50.0",
            "category": "Food",
            "date": "2026-03-20",
            "description": long_desc,
        },
    )
    assert response.status_code == 200
    html = response.get_data(as_text=True)
    assert "200 characters" in html or "error" in html.lower()


# ---------------------------------------------------------------------------
# Navigation tests
# ---------------------------------------------------------------------------


def test_profile_page_has_add_expense_button(test_client):
    """Profile page should have an 'Add Expense' button linking to /expenses/add."""
    client, db_path = test_client
    user = create_user("Nav User 1", "nav1@example.com", "pass12345", db_path=db_path)

    with client.session_transaction() as sess:
        sess["user_id"] = user["id"]
        sess["user_name"] = user["name"]

    response = client.get("/profile")
    assert response.status_code == 200
    html = response.get_data(as_text=True)
    assert 'href="/expenses/add"' in html
    assert "Add Expense" in html


def test_navbar_add_expense_visibility_and_active_state(test_client):
    """Navbar should show Add Expense only when logged in, with active class on /expenses/add."""
    client, db_path = test_client

    # Unauthenticated
    resp_anon = client.get("/")
    assert resp_anon.status_code == 200
    html_anon = resp_anon.get_data(as_text=True)
    assert 'href="/expenses/add"' not in html_anon

    # Authenticated
    user = create_user("Nav User 2", "nav2@example.com", "pass12345", db_path=db_path)
    with client.session_transaction() as sess:
        sess["user_id"] = user["id"]
        sess["user_name"] = user["name"]

    resp_auth = client.get("/")
    assert resp_auth.status_code == 200
    html_auth = resp_auth.get_data(as_text=True)
    assert 'href="/expenses/add"' in html_auth

    # On /expenses/add: active class present on Add Expense link
    resp_add = client.get("/expenses/add")
    assert resp_add.status_code == 200
    html_add = resp_add.get_data(as_text=True)
    assert 'href="/expenses/add" class="active"' in html_add
