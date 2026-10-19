# Spec: Profile Page Design

## Overview

Implements the user profile view (`GET /profile`) for authenticated users, completing Step 4 of the Spendly roadmap. The profile page provides users with a dedicated space to view their account information (display name, email address, account registration date / membership tenure) alongside key spending activity metrics (total expenses logged, total amount tracked) using an account overview card that matches Spendly's warm-paper and forest-green design language. This feature bridges user authentication (Step 3) and expense management (Steps 5–9) by giving users direct access to their account identity, status, and summary in a clean, responsive layout.

## Depends on

- Step 01 (Database Setup) — SQLite database schema, `users` and `expenses` tables, and `get_db()` helper in `database/db.py`.
- Step 02 (Registration) — User creation, password hashing, and user schema.
- Step 03 (Login and Logout) — Session authentication (`session['user_id']`), `get_user_by_id()` helper, and protected route access.

## Routes

- `GET /profile` — Renders the user profile page (`profile.html`) with user details and summary metrics, or redirects unauthenticated visitors to `/login` — logged-in

## Database changes

No database changes.

The `users` and `expenses` tables already exist with all required columns (`users`: `id`, `name`, `email`, `password_hash`, `created_at`; `expenses`: `id`, `user_id`, `amount`, `category`, `date`, `description`).

A new helper function must be added to `database/db.py`:
- `get_user_stats(user_id, db_path=None)` — Queries aggregate expense statistics for the user (total expense count and sum of amounts) using parameterized queries (`?`). Returns a dictionary or `sqlite3.Row` with `total_count` and `total_amount`.

## Templates

- **Create:**
  - `templates/profile.html`
    - Extends `base.html`
    - Injects page-specific CSS in `head` block (`url_for('static', filename='css/profile.css')`)
    - Displays user identity header: user initials avatar badge, user name, and email
    - Displays account details card: member since date, account status
    - Displays summary stat cards: total expenses tracked, total amount spent formatted with rupee symbol (`₹`)
    - Provides quick action links (e.g., Back to Home / Dashboard)
- **Modify:**
  - `templates/base.html`
    - Update the user name indicator in `.nav-links` from a plain `<span>` to an active hyperlink pointing to `{{ url_for('profile') }}`

## Files to change

- `app.py` — Replace the placeholder string in `@app.route("/profile")` with authenticated profile logic that checks `session.get('user_id')`, fetches user data via `get_user_by_id`, fetches aggregate stats via `get_user_stats`, and renders `profile.html`.
- `database/db.py` — Add `get_user_stats(user_id, db_path=None)` helper function using parameterized queries.
- `templates/base.html` — Wrap `session.get('user_name')` in an `<a>` tag with `href="{{ url_for('profile') }}"`.

## Files to create

- `templates/profile.html` — Jinja2 template extending `base.html` for the profile page.
- `static/css/profile.css` — Dedicated stylesheet for profile page components, avatar badge, information cards, and stat widgets.
- `tests/test_profile.py` — Pytest test suite testing unauthenticated redirect, authenticated profile view rendering, correct user data and stats display, and navigation link integration.

## New dependencies

No new dependencies.

## Rules for implementation

- No SQLAlchemy or ORMs
- Parameterised queries only
- Passwords hashed with werkzeug
- Use CSS variables — never hardcode hex values
- All templates extend base.html
- No DB logic inside route functions — keep all database operations in `database/db.py`
- Enforce authentication: unauthenticated requests to `GET /profile` must redirect to `url_for('login')` (HTTP 302)
- Never use raw string returns for implemented routes — always render `profile.html`
- Currency must be formatted with the Indian Rupee symbol (`₹`) and two decimal places (e.g. `₹1,250.00`)
- Page-specific styling must reside in `static/css/profile.css` linked from the template's `head` block; no inline `<style>` tags
- Mobile-responsive design matching breakpoints and typography in `static/css/style.css`
- Keep routes single-responsibility: fetch data, render template, done

## Definition of done

- [ ] Navigating to `GET /profile` while not logged in redirects to `url_for('login')` with HTTP 302
- [ ] Navigating to `GET /profile` with an active session returns HTTP 200 and renders `profile.html` extending `base.html`
- [ ] The profile page correctly displays the user's name, email address, and formatted registration date
- [ ] The profile page displays an initials badge and user stats (total expenses count and total amount spent)
- [ ] Navigation bar in `templates/base.html` turns the user's name into a clickable link to `url_for('profile')` when logged in
- [ ] All new styles in `static/css/profile.css` utilize CSS variables from `style.css` (`--paper`, `--ink`, `--accent`, `--border`, `--radius-md`, etc.)
- [ ] Database helper `get_user_stats()` in `database/db.py` uses parameterized SQL queries and handles users with zero expenses gracefully (returning 0 and 0.0)
- [ ] All new and existing tests pass cleanly with `pytest`
