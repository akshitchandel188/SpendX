import re
from datetime import date, timedelta
import pytest

from app import app
from database.db import init_db, create_user, get_db
from database.queries import (
    get_summary_stats,
    get_recent_transactions,
    get_category_breakdown,
)


# -----------------------------------------------------------------------------
# Fixtures & Test Helpers
# -----------------------------------------------------------------------------

@pytest.fixture
def test_app(tmp_path):
    """Provides an isolated Flask test client and temporary SQLite database."""
    db_file = tmp_path / "test_step6_spendly.db"
    init_db(str(db_file))
    app.config.update({
        "TESTING": True,
        "DATABASE": str(db_file),
        "SECRET_KEY": "test-step6-date-filter-secret-key",
    })
    with app.app_context():
        with app.test_client() as client:
            yield client, str(db_file)


@pytest.fixture
def auth_user(test_app):
    """Creates a standard user and initializes an authenticated session."""
    client, db_path = test_app
    user = create_user("Aarav Sharma", "aarav@example.com", "SecurePass123!", db_path=db_path)
    with client.session_transaction() as sess:
        sess["user_id"] = user["id"]
        sess["user_name"] = user["name"]
    return client, db_path, user


def add_expense(db_path, user_id, amount, category, date_str, description=""):
    """Helper to insert an expense record directly into the test database."""
    conn = get_db(db_path)
    try:
        with conn:
            cursor = conn.cursor()
            cursor.execute(
                """
                INSERT INTO expenses (user_id, amount, category, date, description)
                VALUES (?, ?, ?, ?, ?);
                """,
                (user_id, float(amount), category, str(date_str), description),
            )
            return cursor.lastrowid
    finally:
        conn.close()


def get_preset_dates():
    """Calculates expected preset date bounds according to spec calculations."""
    today = date.today()
    this_month_from = today.replace(day=1).strftime("%Y-%m-%d")
    this_month_to = today.strftime("%Y-%m-%d")
    last_3_months_from = (today - timedelta(days=90)).strftime("%Y-%m-%d")
    last_3_months_to = today.strftime("%Y-%m-%d")
    last_6_months_from = (today - timedelta(days=180)).strftime("%Y-%m-%d")
    last_6_months_to = today.strftime("%Y-%m-%d")
    return {
        "this_month": (this_month_from, this_month_to),
        "last_3_months": (last_3_months_from, last_3_months_to),
        "last_6_months": (last_6_months_from, last_6_months_to),
    }


# -----------------------------------------------------------------------------
# 1. Unfiltered GET /profile (Step 5 preservation & Auth Guard)
# -----------------------------------------------------------------------------

class TestProfileAuthAndUnfiltered:

    def test_unauthenticated_profile_redirects_to_login(self, test_app):
        """Unauthenticated GET /profile must redirect (302) to /login."""
        client, _ = test_app
        response = client.get("/profile")
        assert response.status_code == 302
        assert response.headers["Location"].endswith("/login")

    def test_unauthenticated_profile_with_date_params_redirects_to_login(self, test_app):
        """Unauthenticated GET /profile with date query params must redirect (302) to /login."""
        client, _ = test_app
        response = client.get("/profile?date_from=2026-01-01&date_to=2026-01-31")
        assert response.status_code == 302
        assert response.headers["Location"].endswith("/login")

    def test_unfiltered_profile_defaults_to_all_time(self, auth_user):
        """Visiting /profile with no query params defaults to All Time, showing all user expenses."""
        client, db_path, user = auth_user
        add_expense(db_path, user["id"], 500.00, "Food", "2025-01-15", "Old Meal")
        add_expense(db_path, user["id"], 1500.00, "Bills", "2026-06-20", "Mid Year Rent")
        add_expense(db_path, user["id"], 300.00, "Transport", "2026-10-10", "Metro Pass")

        response = client.get("/profile")
        assert response.status_code == 200
        html = response.get_data(as_text=True)

        # All 3 transactions and all-time total (₹2,300.00) displayed
        assert "Old Meal" in html
        assert "Mid Year Rent" in html
        assert "Metro Pass" in html
        assert "₹2,300.00" in html
        assert "3" in html

        # "All Time" preset button is visually marked active
        assert re.search(r'class="[^"]*preset-btn[^"]*active[^"]*"[^>]*>\s*All Time', html)

    def test_partial_filter_only_date_from_defaults_to_unfiltered(self, auth_user):
        """When only date_from is passed without date_to, falls back to unfiltered All Time view."""
        client, db_path, user = auth_user
        add_expense(db_path, user["id"], 250.00, "Food", "2025-05-10", "Past Snack")
        add_expense(db_path, user["id"], 750.00, "Shopping", "2026-08-15", "Recent Shoes")

        response = client.get("/profile?date_from=2026-01-01")
        assert response.status_code == 200
        html = response.get_data(as_text=True)

        # Unfiltered: both expenses visible, total is 1,000.00
        assert "Past Snack" in html
        assert "Recent Shoes" in html
        assert "₹1,000.00" in html
        assert re.search(r'class="[^"]*preset-btn[^"]*active[^"]*"[^>]*>\s*All Time', html)

    def test_partial_filter_only_date_to_defaults_to_unfiltered(self, auth_user):
        """When only date_to is passed without date_from, falls back to unfiltered All Time view."""
        client, db_path, user = auth_user
        add_expense(db_path, user["id"], 400.00, "Health", "2025-04-01", "Past Checkup")
        add_expense(db_path, user["id"], 600.00, "Entertainment", "2026-09-01", "Concert")

        response = client.get("/profile?date_to=2026-08-01")
        assert response.status_code == 200
        html = response.get_data(as_text=True)

        assert "Past Checkup" in html
        assert "Concert" in html
        assert "₹1,000.00" in html
        assert re.search(r'class="[^"]*preset-btn[^"]*active[^"]*"[^>]*>\s*All Time', html)

    def test_empty_string_date_params_defaults_to_unfiltered(self, auth_user):
        """When date_from and date_to are empty strings, falls back to unfiltered All Time view."""
        client, db_path, user = auth_user
        add_expense(db_path, user["id"], 500.00, "Food", "2026-02-10", "Cafe")

        response = client.get("/profile?date_from=&date_to=")
        assert response.status_code == 200
        html = response.get_data(as_text=True)
        assert "Cafe" in html
        assert "₹500.00" in html
        assert re.search(r'class="[^"]*preset-btn[^"]*active[^"]*"[^>]*>\s*All Time', html)


# -----------------------------------------------------------------------------
# 2. Preset Filters ("This Month", "Last 3 Months", "Last 6 Months", "All Time")
# -----------------------------------------------------------------------------

class TestProfilePresets:

    def test_preset_this_month_filters_expenses_to_current_calendar_month(self, auth_user):
        """'This Month' preset includes expenses within the current month and excludes prior months."""
        client, db_path, user = auth_user
        today = date.today()
        d_from, d_to = get_preset_dates()["this_month"]

        # Expense in current month (today)
        add_expense(db_path, user["id"], 650.00, "Food", today.strftime("%Y-%m-%d"), "Current Month Lunch")
        # Expense 45 days ago (guaranteed previous month)
        prev_month_date = (today - timedelta(days=45)).strftime("%Y-%m-%d")
        add_expense(db_path, user["id"], 1200.00, "Shopping", prev_month_date, "Prior Month Jacket")

        response = client.get(f"/profile?date_from={d_from}&date_to={d_to}")
        assert response.status_code == 200
        html = response.get_data(as_text=True)

        # Only current month expense appears
        assert "Current Month Lunch" in html
        assert "Prior Month Jacket" not in html
        assert "₹650.00" in html
        assert re.search(r'class="[^"]*preset-btn[^"]*active[^"]*"[^>]*>\s*This Month', html)

    def test_preset_last_3_months_filters_to_90_day_window(self, auth_user):
        """'Last 3 Months' preset filters expenses to the 90-day window ending today."""
        client, db_path, user = auth_user
        today = date.today()
        d_from, d_to = get_preset_dates()["last_3_months"]

        # Within 90-day window (20 days ago)
        date_recent = (today - timedelta(days=20)).strftime("%Y-%m-%d")
        add_expense(db_path, user["id"], 420.00, "Transport", date_recent, "Cab Ride")
        # Outside 90-day window (110 days ago)
        date_old = (today - timedelta(days=110)).strftime("%Y-%m-%d")
        add_expense(db_path, user["id"], 990.00, "Bills", date_old, "Old Broadband Bill")

        response = client.get(f"/profile?date_from={d_from}&date_to={d_to}")
        assert response.status_code == 200
        html = response.get_data(as_text=True)

        assert "Cab Ride" in html
        assert "Old Broadband Bill" not in html
        assert "₹420.00" in html
        assert re.search(r'class="[^"]*preset-btn[^"]*active[^"]*"[^>]*>\s*Last 3 Months', html)

    def test_preset_last_6_months_filters_to_180_day_window(self, auth_user):
        """'Last 6 Months' preset filters expenses to the 180-day window ending today."""
        client, db_path, user = auth_user
        today = date.today()
        d_from, d_to = get_preset_dates()["last_6_months"]

        # Within 180-day window (100 days ago)
        date_mid = (today - timedelta(days=100)).strftime("%Y-%m-%d")
        add_expense(db_path, user["id"], 850.00, "Health", date_mid, "Dental Clinic")
        # Outside 180-day window (210 days ago)
        date_very_old = (today - timedelta(days=210)).strftime("%Y-%m-%d")
        add_expense(db_path, user["id"], 1500.00, "Shopping", date_very_old, "Old Coat")

        response = client.get(f"/profile?date_from={d_from}&date_to={d_to}")
        assert response.status_code == 200
        html = response.get_data(as_text=True)

        assert "Dental Clinic" in html
        assert "Old Coat" not in html
        assert "₹850.00" in html
        assert re.search(r'class="[^"]*preset-btn[^"]*active[^"]*"[^>]*>\s*Last 6 Months', html)

    def test_preset_buttons_rendered_with_valid_links(self, auth_user):
        """Preset buttons in the template must link to /profile with calculated parameters."""
        client, _, _ = auth_user
        preset_dates = get_preset_dates()

        response = client.get("/profile")
        assert response.status_code == 200
        html = response.get_data(as_text=True)

        # "This Month" link
        tm_from, tm_to = preset_dates["this_month"]
        assert f"date_from={tm_from}" in html
        assert f"date_to={tm_to}" in html

        # "Last 3 Months" link
        l3_from, l3_to = preset_dates["last_3_months"]
        assert f"date_from={l3_from}" in html
        assert f"date_to={l3_to}" in html

        # "Last 6 Months" link
        l6_from, l6_to = preset_dates["last_6_months"]
        assert f"date_from={l6_from}" in html
        assert f"date_to={l6_to}" in html

        # "All Time" preset must link to clean /profile without query params
        assert 'href="/profile"' in html


# -----------------------------------------------------------------------------
# 3. Custom Date Range Filtering
# -----------------------------------------------------------------------------

class TestProfileCustomDateRange:

    def test_custom_range_filters_summary_stats(self, auth_user):
        """Custom date range correctly limits total spent, transaction count, and top category."""
        client, db_path, user = auth_user
        # Outside range (before)
        add_expense(db_path, user["id"], 1000.00, "Food", "2026-02-15", "February Feast")
        # In range
        add_expense(db_path, user["id"], 500.00, "Transport", "2026-03-05", "Taxi March")
        add_expense(db_path, user["id"], 800.00, "Transport", "2026-03-12", "Train March")
        add_expense(db_path, user["id"], 300.00, "Bills", "2026-03-25", "Water Bill March")
        # Outside range (after)
        add_expense(db_path, user["id"], 2000.00, "Entertainment", "2026-04-10", "April Concert")

        response = client.get("/profile?date_from=2026-03-01&date_to=2026-03-31")
        assert response.status_code == 200
        html = response.get_data(as_text=True)

        # Summary stats: 3 transactions in March, total 1,600.00, top category Transport (1,300)
        assert "₹1,600.00" in html
        assert "3" in html
        assert "Transport" in html

    def test_custom_range_filters_recent_transactions_table(self, auth_user):
        """Only transactions within the custom date range appear in the recent transactions table."""
        client, db_path, user = auth_user
        add_expense(db_path, user["id"], 150.00, "Food", "2026-05-01", "Early May Breakfast")
        add_expense(db_path, user["id"], 350.00, "Food", "2026-05-15", "Mid May Dinner")
        add_expense(db_path, user["id"], 550.00, "Food", "2026-05-28", "Late May Groceries")

        # Filter strictly for 2026-05-10 to 2026-05-20
        response = client.get("/profile?date_from=2026-05-10&date_to=2026-05-20")
        assert response.status_code == 200
        html = response.get_data(as_text=True)

        assert "Mid May Dinner" in html
        assert "Early May Breakfast" not in html
        assert "Late May Groceries" not in html

    def test_custom_range_filters_category_breakdown(self, auth_user):
        """Category breakdown displays only categories and spending within the filtered range."""
        client, db_path, user = auth_user
        # In range: Food (200) and Bills (600)
        add_expense(db_path, user["id"], 200.00, "Food", "2026-07-10", "Groceries")
        add_expense(db_path, user["id"], 600.00, "Bills", "2026-07-20", "Electric Bill")
        # Out of range: Shopping (1500)
        add_expense(db_path, user["id"], 1500.00, "Shopping", "2026-08-05", "Designer Shoes")

        response = client.get("/profile?date_from=2026-07-01&date_to=2026-07-31")
        assert response.status_code == 200
        html = response.get_data(as_text=True)

        # Food and Bills appear with filtered totals (₹200.00 and ₹600.00)
        assert "Food" in html
        assert "Bills" in html
        assert "₹200.00" in html
        assert "₹600.00" in html

        # Shopping is outside July and should NOT appear in category breakdown or stats
        assert "Designer Shoes" not in html
        assert "₹1,500.00" not in html

    def test_custom_range_inclusive_boundary_dates(self, auth_user):
        """Expenses on exact date_from and date_to dates must be included (inclusive bounds)."""
        client, db_path, user = auth_user
        add_expense(db_path, user["id"], 100.00, "Other", "2026-08-31", "Day Before Bound")
        add_expense(db_path, user["id"], 250.00, "Food", "2026-09-01", "Start Date Bound Expense")
        add_expense(db_path, user["id"], 500.00, "Transport", "2026-09-15", "Middle Expense")
        add_expense(db_path, user["id"], 750.00, "Bills", "2026-09-30", "End Date Bound Expense")
        add_expense(db_path, user["id"], 120.00, "Other", "2026-10-01", "Day After Bound")

        response = client.get("/profile?date_from=2026-09-01&date_to=2026-09-30")
        assert response.status_code == 200
        html = response.get_data(as_text=True)

        # Boundaries (Sep 1 and Sep 30) and middle (Sep 15) included: total 1,500.00, count 3
        assert "Start Date Bound Expense" in html
        assert "Middle Expense" in html
        assert "End Date Bound Expense" in html
        assert "Day Before Bound" not in html
        assert "Day After Bound" not in html
        assert "₹1,500.00" in html
        assert "3" in html

    def test_custom_range_single_day(self, auth_user):
        """When date_from == date_to, exactly expenses on that single day are matched."""
        client, db_path, user = auth_user
        add_expense(db_path, user["id"], 110.00, "Food", "2026-04-14", "Day Prior")
        add_expense(db_path, user["id"], 440.00, "Entertainment", "2026-04-15", "Target Day Movie")
        add_expense(db_path, user["id"], 220.00, "Food", "2026-04-16", "Day Next")

        response = client.get("/profile?date_from=2026-04-15&date_to=2026-04-15")
        assert response.status_code == 200
        html = response.get_data(as_text=True)

        assert "Target Day Movie" in html
        assert "Day Prior" not in html
        assert "Day Next" not in html
        assert "₹440.00" in html
        assert "1" in html


# -----------------------------------------------------------------------------
# 4. Validation Errors & Fallback Behavior
# -----------------------------------------------------------------------------

class TestProfileDateValidation:

    def test_date_from_greater_than_date_to_flashes_error_and_falls_back(self, auth_user):
        """When date_from > date_to, flashes error message and falls back to unfiltered All Time view."""
        client, db_path, user = auth_user
        add_expense(db_path, user["id"], 300.00, "Food", "2026-01-10", "January Lunch")
        add_expense(db_path, user["id"], 700.00, "Shopping", "2026-05-15", "May Clothes")

        response = client.get("/profile?date_from=2026-05-20&date_to=2026-05-10")
        assert response.status_code == 200
        html = response.get_data(as_text=True)

        # Flashes user-visible error message
        assert "Start date must be before end date." in html

        # Falls back to unfiltered view: both expenses displayed, total ₹1,000.00
        assert "January Lunch" in html
        assert "May Clothes" in html
        assert "₹1,000.00" in html

        # Falls back to All Time preset active state
        assert re.search(r'class="[^"]*preset-btn[^"]*active[^"]*"[^>]*>\s*All Time', html)

    def test_malformed_date_from_silently_falls_back(self, auth_user):
        """Malformed date_from string silently falls back to unfiltered view without crashing."""
        client, db_path, user = auth_user
        add_expense(db_path, user["id"], 450.00, "Health", "2026-03-10", "Vitamins")

        response = client.get("/profile?date_from=invalid-date&date_to=2026-03-31")
        assert response.status_code == 200
        html = response.get_data(as_text=True)

        assert "Vitamins" in html
        assert "₹450.00" in html
        assert re.search(r'class="[^"]*preset-btn[^"]*active[^"]*"[^>]*>\s*All Time', html)

    def test_malformed_date_to_silently_falls_back(self, auth_user):
        """Malformed date_to string silently falls back to unfiltered view without crashing."""
        client, db_path, user = auth_user
        add_expense(db_path, user["id"], 350.00, "Transport", "2026-04-12", "Fuel")

        response = client.get("/profile?date_from=2026-04-01&date_to=31-04-2026")
        assert response.status_code == 200
        html = response.get_data(as_text=True)

        assert "Fuel" in html
        assert "₹350.00" in html
        assert re.search(r'class="[^"]*preset-btn[^"]*active[^"]*"[^>]*>\s*All Time', html)

    def test_both_dates_malformed_silently_falls_back(self, auth_user):
        """When both date params are arbitrary garbage strings, silently falls back to unfiltered view."""
        client, db_path, user = auth_user
        add_expense(db_path, user["id"], 820.00, "Bills", "2026-06-01", "Phone Bill")

        response = client.get("/profile?date_from=bad_start&date_to=bad_end")
        assert response.status_code == 200
        html = response.get_data(as_text=True)

        assert "Phone Bill" in html
        assert "₹820.00" in html
        assert re.search(r'class="[^"]*preset-btn[^"]*active[^"]*"[^>]*>\s*All Time', html)

    def test_invalid_calendar_date_silently_falls_back(self, auth_user):
        """Calendar dates that do not exist (e.g. Feb 31) fail parse and fall back safely."""
        client, db_path, user = auth_user
        add_expense(db_path, user["id"], 150.00, "Other", "2026-01-01", "New Year Gift")

        response = client.get("/profile?date_from=2026-02-31&date_to=2026-03-15")
        assert response.status_code == 200
        html = response.get_data(as_text=True)

        assert "New Year Gift" in html
        assert "₹150.00" in html

    def test_non_iso_date_formats_silently_fall_back(self, auth_user):
        """Date formats with slashes or timestamps instead of YYYY-MM-DD fall back silently."""
        client, db_path, user = auth_user
        add_expense(db_path, user["id"], 600.00, "Food", "2026-07-04", "Dinner")

        response = client.get("/profile?date_from=2026/07/01&date_to=2026/07/31")
        assert response.status_code == 200
        html = response.get_data(as_text=True)

        assert "Dinner" in html
        assert "₹600.00" in html


# -----------------------------------------------------------------------------
# 5. Out of Range & Empty State Behavior
# -----------------------------------------------------------------------------

class TestProfileEmptyAndBoundaryStates:

    def test_date_range_with_no_matching_expenses_shows_clean_empty_states(self, auth_user):
        """When date filter matches 0 expenses, displays ₹0.00, 0 count, —, and clean empty cards."""
        client, db_path, user = auth_user
        # User has expenses in 2026
        add_expense(db_path, user["id"], 500.00, "Food", "2026-05-10", "May Expense")

        # Query range in 2020 where no expenses exist
        response = client.get("/profile?date_from=2020-01-01&date_to=2020-01-31")
        assert response.status_code == 200
        html = response.get_data(as_text=True)

        # Stats clean defaults
        assert "₹0.00" in html
        assert "—" in html

        # Empty landmarks rendered
        assert "No expenses logged yet." in html
        assert "No category spending yet." in html

    def test_user_with_no_expenses_at_all_applying_filter_renders_cleanly(self, auth_user):
        """User with zero expenses applying any date filter renders 200 OK without errors."""
        client, _, _ = auth_user
        response = client.get("/profile?date_from=2026-01-01&date_to=2026-12-31")
        assert response.status_code == 200
        html = response.get_data(as_text=True)

        assert "₹0.00" in html
        assert "No expenses logged yet." in html
        assert "No category spending yet." in html


# -----------------------------------------------------------------------------
# 6. UI Indicators & Template Landmarks
# -----------------------------------------------------------------------------

class TestProfileUIAndLandmarks:

    def test_active_preset_button_highlighted_for_presets(self, auth_user):
        """Active preset button is highlighted with the 'active' class for each preset."""
        client, _, _ = auth_user
        presets = get_preset_dates()

        # 1. This Month
        tm_from, tm_to = presets["this_month"]
        res_tm = client.get(f"/profile?date_from={tm_from}&date_to={tm_to}")
        assert res_tm.status_code == 200
        assert re.search(r'class="[^"]*preset-btn[^"]*active[^"]*"[^>]*>\s*This Month', res_tm.get_data(as_text=True))

        # 2. Last 3 Months
        l3_from, l3_to = presets["last_3_months"]
        res_l3 = client.get(f"/profile?date_from={l3_from}&date_to={l3_to}")
        assert res_l3.status_code == 200
        assert re.search(r'class="[^"]*preset-btn[^"]*active[^"]*"[^>]*>\s*Last 3 Months', res_l3.get_data(as_text=True))

        # 3. Last 6 Months
        l6_from, l6_to = presets["last_6_months"]
        res_l6 = client.get(f"/profile?date_from={l6_from}&date_to={l6_to}")
        assert res_l6.status_code == 200
        assert re.search(r'class="[^"]*preset-btn[^"]*active[^"]*"[^>]*>\s*Last 6 Months', res_l6.get_data(as_text=True))

    def test_custom_range_populates_input_values_and_highlights_apply_button(self, auth_user):
        """Submitting a custom date range populates the input fields and adds 'active' class to Apply."""
        client, _, _ = auth_user
        custom_from = "2026-03-10"
        custom_to = "2026-03-25"

        response = client.get(f"/profile?date_from={custom_from}&date_to={custom_to}")
        assert response.status_code == 200
        html = response.get_data(as_text=True)

        # Values preserved in custom form inputs
        assert f'value="{custom_from}"' in html
        assert f'value="{custom_to}"' in html

        # Apply button has active state
        assert re.search(r'class="[^"]*filter-apply-btn[^"]*active[^"]*"', html)

        # Preset buttons must NOT have active class
        assert not re.search(r'class="[^"]*preset-btn[^"]*active[^"]*"[^>]*>\s*All Time', html)
        assert not re.search(r'class="[^"]*preset-btn[^"]*active[^"]*"[^>]*>\s*This Month', html)

    def test_rupee_symbol_consistently_present_in_filtered_view(self, auth_user):
        """Currency symbol (₹) is always rendered for amounts in filtered profile view."""
        client, db_path, user = auth_user
        add_expense(db_path, user["id"], 880.00, "Bills", "2026-08-10", "Electricity")

        response = client.get("/profile?date_from=2026-08-01&date_to=2026-08-31")
        assert response.status_code == 200
        html = response.get_data(as_text=True)

        # Rupee symbol appears in total spent and table row
        assert "₹880.00" in html
        assert "₹" in html


# -----------------------------------------------------------------------------
# 7. User Data Isolation
# -----------------------------------------------------------------------------

class TestUserDataIsolation:

    def test_date_filter_strictly_isolates_user_expenses(self, auth_user):
        """Date filtering must only query and return expenses belonging to the authenticated user."""
        client, db_path, user1 = auth_user
        user2 = create_user("Second User", "second@example.com", "Password456!", db_path=db_path)

        # Both users log expenses on 2026-06-15
        add_expense(db_path, user1["id"], 300.00, "Food", "2026-06-15", "User1 Food")
        add_expense(db_path, user2["id"], 9000.00, "Shopping", "2026-06-15", "User2 Shopping")

        response = client.get("/profile?date_from=2026-06-01&date_to=2026-06-30")
        assert response.status_code == 200
        html = response.get_data(as_text=True)

        # User 1 sees only their own expense
        assert "User1 Food" in html
        assert "₹300.00" in html
        assert "User2 Shopping" not in html
        assert "₹9,000.00" not in html


# -----------------------------------------------------------------------------
# 8. Pure Query Helpers Unit Tests (database/queries/)
# -----------------------------------------------------------------------------

class TestDatabaseQueryHelpers:

    def test_get_summary_stats_unfiltered_and_filtered(self, test_app):
        """get_summary_stats respects date_from and date_to parameters and falls back when absent."""
        _, db_path = test_app
        user = create_user("Query User", "queryuser@example.com", "Pass123!", db_path=db_path)
        u_id = user["id"]

        add_expense(db_path, u_id, 200.00, "Food", "2026-01-10")
        add_expense(db_path, u_id, 300.00, "Transport", "2026-02-15")
        add_expense(db_path, u_id, 500.00, "Transport", "2026-02-20")

        # Unfiltered
        unfiltered = get_summary_stats(u_id, db_path=db_path)
        assert unfiltered["transaction_count"] == 3
        assert unfiltered["total_spent"] == 1000.00
        assert unfiltered["top_category"] == "Transport"

        # Filtered for February 2026
        filtered = get_summary_stats(u_id, date_from="2026-02-01", date_to="2026-02-28", db_path=db_path)
        assert filtered["transaction_count"] == 2
        assert filtered["total_spent"] == 800.00
        assert filtered["top_category"] == "Transport"

        # Filtered with single bound (treated as unfiltered)
        partial_from = get_summary_stats(u_id, date_from="2026-02-01", date_to=None, db_path=db_path)
        assert partial_from["transaction_count"] == 3

    def test_get_summary_stats_empty_range_returns_defaults(self, test_app):
        """get_summary_stats returns clean defaults when no expenses fall within the range."""
        _, db_path = test_app
        user = create_user("Empty User", "empty@example.com", "Pass123!", db_path=db_path)
        add_expense(db_path, user["id"], 100.00, "Food", "2026-05-01")

        result = get_summary_stats(user["id"], date_from="2020-01-01", date_to="2020-01-31", db_path=db_path)
        assert result["total_spent"] == 0.0
        assert result["transaction_count"] == 0
        assert result["top_category"] == "—"

    def test_get_recent_transactions_filters_by_date_and_orders_desc(self, test_app):
        """get_recent_transactions filters within date range and orders newest first (date DESC, id DESC)."""
        _, db_path = test_app
        user = create_user("Tx User", "txuser@example.com", "Pass123!", db_path=db_path)
        u_id = user["id"]

        add_expense(db_path, u_id, 100.00, "Food", "2026-03-01", "Early March")
        add_expense(db_path, u_id, 200.00, "Bills", "2026-03-15", "Mid March A")
        add_expense(db_path, u_id, 300.00, "Bills", "2026-03-15", "Mid March B")
        add_expense(db_path, u_id, 400.00, "Health", "2026-03-31", "Late March")
        add_expense(db_path, u_id, 500.00, "Other", "2026-04-05", "April Expense")

        txs = get_recent_transactions(u_id, limit=10, date_from="2026-03-05", date_to="2026-03-31", db_path=db_path)
        assert len(txs) == 3
        # Ordering check: date DESC, id DESC
        assert txs[0]["description"] == "Late March"
        assert txs[1]["description"] == "Mid March B"
        assert txs[2]["description"] == "Mid March A"

    def test_get_recent_transactions_empty_range_returns_empty_list(self, test_app):
        """get_recent_transactions returns [] when date range contains no transactions."""
        _, db_path = test_app
        user = create_user("NoTx User", "notx@example.com", "Pass123!", db_path=db_path)
        add_expense(db_path, user["id"], 100.00, "Food", "2026-05-01")

        result = get_recent_transactions(user["id"], date_from="2020-01-01", date_to="2020-01-31", db_path=db_path)
        assert result == []

    def test_get_category_breakdown_with_and_without_date_filter(self, test_app):
        """get_category_breakdown computes percentages summing to 100 for filtered subsets."""
        _, db_path = test_app
        user = create_user("Cat User", "catuser@example.com", "Pass123!", db_path=db_path)
        u_id = user["id"]

        add_expense(db_path, u_id, 300.00, "Food", "2026-06-01")
        add_expense(db_path, u_id, 700.00, "Transport", "2026-06-15")
        add_expense(db_path, u_id, 2000.00, "Bills", "2026-07-01")

        # Filter strictly for June 2026
        breakdown = get_category_breakdown(u_id, date_from="2026-06-01", date_to="2026-06-30", db_path=db_path)
        assert len(breakdown) == 2
        categories = [item["category"] for item in breakdown]
        assert "Transport" in categories
        assert "Food" in categories
        assert "Bills" not in categories

        # Percentage sum check
        pct_sum = sum(item["pct"] for item in breakdown)
        assert pct_sum == 100

    def test_get_category_breakdown_empty_range_returns_empty_list(self, test_app):
        """get_category_breakdown returns [] when no expenses exist in the date range."""
        _, db_path = test_app
        user = create_user("EmptyCat User", "emptycat@example.com", "Pass123!", db_path=db_path)
        add_expense(db_path, user["id"], 100.00, "Food", "2026-05-01")

        result = get_category_breakdown(user["id"], date_from="2020-01-01", date_to="2020-01-31", db_path=db_path)
        assert result == []
