import os
import re
from datetime import datetime
from flask import Flask, render_template, request, redirect, url_for, session
from werkzeug.security import check_password_hash
from database.db import (
    get_db,
    init_db,
    seed_db,
    get_user_by_email,
    get_user_by_id,
    create_user,
    get_user_stats,
    get_recent_expenses,
    get_category_spending,
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

    member_since = format_member_since(user["created_at"])
    stats = get_user_stats(user_id)
    recent_expenses = get_recent_expenses(user_id, limit=8)
    category_spending = get_category_spending(user_id)

    return render_template(
        "profile.html",
        user=user,
        initials=initials,
        member_since=member_since,
        stats=stats,
        recent_expenses=recent_expenses,
        category_spending=category_spending,
    )


@app.route("/expenses/add")
def add_expense():
    return "Add expense — coming in Step 7"


@app.route("/expenses/<int:id>/edit")
def edit_expense(id):
    return "Edit expense — coming in Step 8"


@app.route("/expenses/<int:id>/delete")
def delete_expense(id):
    return "Delete expense — coming in Step 9"


if __name__ == "__main__":
    app.run(debug=True, port=5001)
