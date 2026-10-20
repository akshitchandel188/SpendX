# Spec: Backend Routes for Profile Page

## Overview

Wires the `/profile` route to live database queries against SQLite, completing Step 5 of the Spendly roadmap. Following the static UI layout established in Step 4, this step implements dedicated, pure query helpers to dynamically fetch and compute user account data, overall spending summary stats, recent transaction history, and category spending breakdown. This connects the profile view to real user data so that authenticated users immediately see their own expenses, metrics, and activity in Spendly's warm-paper and forest-green interface.

## Depends on

- Step 01 (Database Setup) — SQLite database schema, `users` and `expenses` tables, sample seed data, and `get_db()` helper in `database/db.py`.
- Step 02 (Registration) — Users stored in the database with hashed passwords.
- Step 03 (Login and Logout) — Session authentication (`session["user_id"]`) and protected route access.
- Step 04 (Profile Page Design) — Profile layout in `templates/profile.html` and stylesheet `static/css/profile.css`.

## Routes

No new routes.

Existing route modified:
- `GET /profile` — Queries live data from SQLite for the authenticated user and renders `templates/profile.html` — logged-in

## Database changes

No database changes.

The `users` and `expenses` tables already exist in `database/db.py` with all required columns (`users`: `id`, `name`, `email`, `password_hash`, `created_at`; `expenses`: `id`, `user_id`, `amount`, `category`, `date`, `description`, `created_at`).

## Templates

- **Create:** None
- **Modify:**
  - `templates/profile.html`
    - Display dynamic user info (`name`, `email`, `member_since`, `initials`)
    - Display summary metrics (`total_spent`, `transaction_count`, `top_category`)
    - Display recent transactions list with formatted dates, descriptions, categories, and amounts
    - Display category breakdown with category names, total amounts, and integer percentage widths (`pct`)
    - Ensure all currency values display with the Indian Rupee symbol (`₹`) and two decimal places

## Files to change

- `app.py` — Update `profile()` route handler to import and call query helpers, pass dynamic data to `profile.html`, and maintain unauthenticated redirection to `url_for('login')`.
- `templates/profile.html` — Bind dynamic variables from query helpers (`user`, `summary_stats`, `recent_transactions`, `category_breakdown`) and verify currency formatting.
- `database/db.py` — Ensure `get_db()` supports connection access for query helpers with `PRAGMA foreign_keys = ON;`, and re-export query helpers if needed.

## Files to create

- `database/queries.py` — Pure query helpers (no Flask imports) using parameterized SQL (`?`) and `get_db()`:
  - `get_user_by_id(user_id, db_path=None)` → dict with `name`, `email`, `member_since` (formatted as "Month YYYY")
  - `get_summary_stats(user_id, db_path=None)` → dict with `total_spent` (float), `transaction_count` (int), `top_category` (str)
  - `get_recent_transactions(user_id, limit=10, db_path=None)` → list of dicts, each with `id`, `date`, `description`, `category`, `amount`
  - `get_category_breakdown(user_id, db_path=None)` → list of dicts, each with `name`, `amount`, `pct` (integer percentage of total spent, summing to 100)
- `tests/test_backend_connection.py` — Pytest suite covering unit tests for each query helper and integration route tests for `GET /profile`.

## New dependencies

No new dependencies.

## Rules for implementation

- No SQLAlchemy or ORMs — raw `sqlite3` only via `get_db()`
- Parameterised queries only — never string-format or use f-strings in SQL
- Foreign keys PRAGMA must be enabled on every connection (`PRAGMA foreign_keys = ON;` via `get_db()`)
- Use CSS variables — never hardcode hex values
- All templates extend `base.html`
- No inline styles in HTML templates
- Currency must always display as ₹ — never $ or £
- Route functions: one responsibility only — fetch data, render template, done
- Query helpers in `database/queries.py` must call `get_db(db_path)` internally, manage connections with `try...finally` ensuring `conn.close()`, and return native Python types (dicts, lists, ints, floats)
- Empty state resilience: if a user has zero expenses, `get_summary_stats` must return `{"total_spent": 0.0, "transaction_count": 0, "top_category": "—"}` and `get_recent_transactions` / `get_category_breakdown` must return empty lists `[]` without raising errors
- Integer percentage normalization: `pct` values in `get_category_breakdown` must sum to 100 when expenses exist, absorbing any integer rounding remainder into the largest category

## Definition of done

- [ ] `database/queries.py` implements all 4 query helpers with parameterized queries and explicit connection closure
- [ ] `get_user_by_id` returns correct user dictionary with `name`, `email`, and formatted `member_since` ("Month YYYY"), or `None` for non-existent ID
- [ ] `get_summary_stats` returns correct `total_spent`, `transaction_count`, and `top_category` for users with expenses, and `0.0`, `0`, `"—"` for users with zero expenses
- [ ] `get_recent_transactions` returns expenses ordered newest date first (`date DESC, id DESC`) limited to the requested count
- [ ] `get_category_breakdown` returns category list sorted descending by amount with integer `pct` values summing to 100%
- [ ] Navigating to `GET /profile` while unauthenticated redirects to `url_for('login')` with HTTP 302
- [ ] Navigating to `GET /profile` authenticated as the seed user (`demo@spendly.com`) returns HTTP 200 and renders live stats, transactions, category breakdown, and ₹ symbol
- [ ] Registering a new user and viewing `/profile` displays ₹0.00 total spent, 0 transactions, empty breakdown state, and no errors
- [ ] All unit and route tests in `tests/test_backend_connection.py` and existing test suites pass cleanly with `pytest`
