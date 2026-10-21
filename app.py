import os
import re
from datetime import datetime, date, timedelta
from flask import Flask, render_template, request, redirect, url_for, session, flash, abort
from werkzeug.security import check_password_hash
from database.db import (
    get_db,
    init_db,
    seed_db,
    get_user_by_email,
    create_user,
    CATEGORIES,
)
from database.queries import (
    get_user_by_id,
    get_summary_stats,
    get_recent_transactions,
    get_category_breakdown,
    insert_expense,
    get_expense_by_id,
    update_expense,
)

app = Flask(__name__)
app.secret_key = os.environ.get("SECRET_KEY", "dev-secret-key-spendly-fallback")

EMAIL_REGEX = re.compile(r"^[^@\s]+@[^@\s]+\.[^@\s]+$")

with app.app_context():
    init_db()
    seed_db()


# ------------------------------------------------------------------ #
# Routes                                                              #
# ------------------------------------------------------------------ #

@app.route("/")
def landing():
    return render_template("landing.html")


@app.route("/register", methods=["GET", "POST"])
def register():
    if session.get("user_id"):
        return redirect(url_for("landing"))

    if request.method == "POST":
        name = request.form.get("name", "").strip()
        email = request.form.get("email", "").strip().lower()
        password = request.form.get("password", "")

        if not name or not email or not password:
            return render_template(
                "register.html",
                error="All fields are required.",
                name=name,
                email=email,
            ), 400

        if not EMAIL_REGEX.match(email):
            return render_template(
                "register.html",
                error="Please enter a valid email address.",
                name=name,
                email=email,
            ), 400

        if len(password) < 8:
            return render_template(
                "register.html",
                error="Password must be at least 8 characters long.",
                name=name,
                email=email,
            ), 400

        if get_user_by_email(email):
            return render_template(
                "register.html",
                error="An account with this email already exists.",
                name=name,
                email=email,
            ), 400

        try:
            create_user(name, email, password)
        except Exception:
            return render_template(
                "register.html",
                error="An error occurred while creating your account. Please try again.",
                name=name,
                email=email,
            ), 400

        return redirect(url_for("login"))

    return render_template("register.html")


@app.route("/login", methods=["GET", "POST"])
def login():
    if session.get("user_id"):
        return redirect(url_for("profile"))

    if request.method == "POST":
        email = request.form.get("email", "").strip().lower()
        password = request.form.get("password", "")

        if not email or not password:
            return render_template(
                "login.html",
                error="All fields are required.",
                email=email,
            ), 400

        user = get_user_by_email(email)
        if not user or not check_password_hash(user["password_hash"], password):
            return render_template(
                "login.html",
                error="Invalid email or password.",
                email=email,
            ), 401

        session["user_id"] = user["id"]
        session["user_name"] = user["name"]
        return redirect(url_for("profile"))

    return render_template("login.html")


@app.route("/logout")
def logout():
    session.clear()
    return redirect(url_for("login"))


@app.route("/terms")
def terms():
    return render_template("terms.html")


@app.route("/privacy")
def privacy():
    return render_template("privacy.html")


# ------------------------------------------------------------------ #
# Placeholder routes — students will implement these                  #
# ------------------------------------------------------------------ #


def format_member_since(raw_date):
    if not raw_date:
        return "N/A"
    try:
        dt = datetime.strptime(str(raw_date)[:19], "%Y-%m-%d %H:%M:%S")
        return dt.strftime("%B %d, %Y")
    except Exception:
        try:
            dt = datetime.strptime(str(raw_date)[:10], "%Y-%m-%d")
            return dt.strftime("%B %d, %Y")
        except Exception:
            return str(raw_date)


def format_short_date(date_str):
    if not date_str:
        return ""
    try:
        dt = datetime.strptime(str(date_str)[:10], "%Y-%m-%d")
        return dt.strftime("%d %b %Y")
    except Exception:
        return str(date_str)


@app.template_filter("short_date")
def short_date_filter(date_str):
    return format_short_date(date_str)


def get_date_presets(today=None):
    """Compute rolling date bounds for quick-select filter presets."""
    today = today or date.today()
    this_month_from = today.replace(day=1).strftime("%Y-%m-%d")
    today_str = today.strftime("%Y-%m-%d")
    return {
        "this_month": {
            "date_from": this_month_from,
            "date_to": today_str,
            "label": "This Month",
        },
        "last_3_months": {
            "date_from": (today - timedelta(days=90)).strftime("%Y-%m-%d"),
            "date_to": today_str,
            "label": "Last 3 Months",
        },
        "last_6_months": {
            "date_from": (today - timedelta(days=180)).strftime("%Y-%m-%d"),
            "date_to": today_str,
            "label": "Last 6 Months",
        },
    }


def parse_date_filter(raw_from, raw_to):
    """
    Parse and validate raw date parameters from query string.
    Returns:
        (filter_date_from, filter_date_to, error_message)
    """
    if not (raw_from and raw_to):
        return None, None, None
    try:
        d_from = datetime.strptime(raw_from, "%Y-%m-%d").date()
        d_to = datetime.strptime(raw_to, "%Y-%m-%d").date()
        if d_from > d_to:
            return None, None, "Start date must be before end date."
        return d_from.strftime("%Y-%m-%d"), d_to.strftime("%Y-%m-%d"), None
    except ValueError:
        return None, None, None


def get_active_preset(filter_date_from, filter_date_to, presets):
    """Determine which preset matches the active date bounds."""
    if not filter_date_from or not filter_date_to:
        return "all_time"
    for preset_key, preset in presets.items():
        if filter_date_from == preset["date_from"] and filter_date_to == preset["date_to"]:
            return preset_key
    return "custom"


@app.route("/profile")
def profile():
    user_id = session.get("user_id")
    if not user_id:
        return redirect(url_for("login"))

    user = get_user_by_id(user_id)
    if not user:
        session.clear()
        return redirect(url_for("login"))

    name_parts = user["name"].strip().split()
    initials = (name_parts[0][0] + (name_parts[-1][0] if len(name_parts) > 1 else "")).upper() if name_parts else "U"
    member_since = user.get("member_since") or format_member_since(user.get("created_at"))

    presets = get_date_presets()
    raw_date_from = request.args.get("date_from", "").strip()
    raw_date_to = request.args.get("date_to", "").strip()
    filter_date_from, filter_date_to, err = parse_date_filter(raw_date_from, raw_date_to)
    if err:
        flash(err, "error")

    active_preset = get_active_preset(filter_date_from, filter_date_to, presets)

    # Query helpers with optional date filters
    stats = get_summary_stats(user_id, date_from=filter_date_from, date_to=filter_date_to)
    recent_transactions = get_recent_transactions(
        user_id,
        limit=10,
        date_from=filter_date_from,
        date_to=filter_date_to,
    )
    category_breakdown = get_category_breakdown(
        user_id,
        date_from=filter_date_from,
        date_to=filter_date_to,
    )

    return render_template(
        "profile.html",
        user=user,
        initials=initials,
        member_since=member_since,
        stats=stats,
        summary_stats=stats,
        recent_expenses=recent_transactions,
        recent_transactions=recent_transactions,
        category_spending=category_breakdown,
        category_breakdown=category_breakdown,
        date_from=filter_date_from or "",
        date_to=filter_date_to or "",
        active_preset=active_preset,
        presets=presets,
    )


@app.route("/analytics")
def analytics():
    """Render the analytics coming soon page for authenticated users."""
    user_id = session.get("user_id")
    if not user_id:
        return redirect(url_for("login"))

    user = get_user_by_id(user_id)
    if not user:
        session.clear()
        return redirect(url_for("login"))

    return render_template("analytics.html", user=user)


@app.route("/expenses/add", methods=["GET", "POST"])
def add_expense():
    """Add a new expense for the authenticated user."""
    user_id = session.get("user_id")
    if not user_id:
        return redirect(url_for("login"))

    user = get_user_by_id(user_id)
    if not user:
        session.clear()
        return redirect(url_for("login"))

    today_str = date.today().strftime("%Y-%m-%d")

    if request.method == "POST":
        amount_raw = request.form.get("amount", "").strip()
        category = request.form.get("category", "").strip()
        date_raw = request.form.get("date", "").strip()
        description = request.form.get("description", "").strip()

        error = None
        amount = None

        if not amount_raw:
            error = "Please enter an amount."
        else:
            try:
                amount = float(amount_raw)
                if amount <= 0:
                    error = "Amount must be greater than zero."
            except ValueError:
                error = "Amount must be a valid number."

        if not error:
            if not category or category not in CATEGORIES:
                error = "Please select a valid category."

        if not error:
            if not date_raw:
                error = "Please select a valid date."
            else:
                try:
                    datetime.strptime(date_raw, "%Y-%m-%d")
                except ValueError:
                    error = "Date must be a valid date in YYYY-MM-DD format."

        if not error and len(description) > 200:
            error = "Description cannot exceed 200 characters."

        if error:
            return (
                render_template(
                    "add_expense.html",
                    error=error,
                    amount=amount_raw,
                    category=category,
                    date=date_raw or today_str,
                    description=description,
                    categories=CATEGORIES,
                    today=today_str,
                ),
                200,
            )

        insert_expense(
            user_id=user_id,
            amount=amount,
            category=category,
            date=date_raw,
            description=description or None,
        )
        return redirect(url_for("profile"))

    return render_template(
        "add_expense.html",
        categories=CATEGORIES,
        today=today_str,
        date=today_str,
        amount="",
        category="",
        description="",
    )


@app.route("/expenses/<int:id>/edit", methods=["GET", "POST"])
def edit_expense(id):
    """Edit an existing expense for the authenticated user."""
    user_id = session.get("user_id")
    if not user_id:
        return redirect(url_for("login"))

    user = get_user_by_id(user_id)
    if not user:
        session.clear()
        return redirect(url_for("login"))

    expense = get_expense_by_id(id, user_id=user_id)
    if not expense:
        abort(404)

    if request.method == "POST":
        amount_raw = request.form.get("amount", "").strip()
        category = request.form.get("category", "").strip()
        date_raw = request.form.get("date", "").strip()
        description = request.form.get("description", "").strip()

        error = None
        amount = None

        if not amount_raw:
            error = "Please enter an amount."
        else:
            try:
                amount = float(amount_raw)
                if amount <= 0:
                    error = "Amount must be greater than zero."
            except ValueError:
                error = "Amount must be a valid number."

        if not error:
            if not category or category not in CATEGORIES:
                error = "Please select a valid category."

        if not error:
            if not date_raw:
                error = "Please select a valid date."
            else:
                try:
                    datetime.strptime(date_raw, "%Y-%m-%d")
                except ValueError:
                    error = "Date must be a valid date in YYYY-MM-DD format."

        if not error and len(description) > 200:
            error = "Description cannot exceed 200 characters."

        if error:
            return (
                render_template(
                    "edit_expense.html",
                    error=error,
                    expense=expense,
                    amount=amount_raw,
                    category=category,
                    date=date_raw,
                    description=description,
                    categories=CATEGORIES,
                ),
                200,
            )

        update_expense(
            expense_id=id,
            user_id=user_id,
            amount=amount,
            category=category,
            date=date_raw,
            description=description or None,
        )
        return redirect(url_for("profile"))

    return render_template(
        "edit_expense.html",
        expense=expense,
        amount=expense["amount"],
        category=expense["category"],
        date=expense["date"],
        description=expense["description"],
        categories=CATEGORIES,
    )


@app.route("/expenses/<int:id>/delete")
def delete_expense(id):
    return "Delete expense — coming in Step 9"


if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5001))
    debug = os.environ.get("FLASK_DEBUG", "false").lower() in ("true", "1")
    app.run(host="0.0.0.0", port=port, debug=debug)
