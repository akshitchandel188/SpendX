# Spec: Login and Logout

## Overview

Authenticate registered users and manage active user sessions using Flask's secure session cookies. This feature completes Step 3 of the Spendly roadmap by enabling existing users to sign in with their email and password, establishing and maintaining authenticated session state across requests, updating the navigation bar to reflect login state, and providing a clean logout mechanism to end sessions. It establishes essential authentication infrastructure required before implementing protected profile management and personal expense tracking in subsequent steps.

## Depends on

- Step 01 (Database Setup) — SQLite database schema, `users` table, and `get_db()` helper in `database/db.py`.
- Step 02 (Registration) — User registration workflow, `get_user_by_email()` helper, and password hashing with `werkzeug.security`.

## Routes

- `GET /login` — Renders the login form page (`login.html`), or redirects authenticated users to `/` if already logged in — public
- `POST /login` — Validates credentials against stored password hash using `check_password_hash`, initializes user session (`session['user_id']`, `session['user_name']`), and redirects to `/` — public
- `GET /logout` — Clears user session (`session.clear()`) and redirects to `/login` — logged-in

## Database changes

No database changes.

The `users` table schema already exists with the necessary columns (`id`, `name`, `email`, `password_hash`, `created_at`). New user data access helper must be added to `database/db.py`:
- `get_user_by_id(user_id, db_path=None)` — Look up user by primary key ID from session data

## Templates

- **Create:** None
- **Modify:**
  - `templates/login.html`
    - Update `<form>` action to `{{ url_for('login') }}` instead of hardcoded `/login`
    - Ensure error message container renders when `error` is passed from the route
    - Preserve submitted `email` value on validation or authentication errors (`value="{{ email or '' }}"`)
    - Keep password field cleared on error
  - `templates/base.html`
    - Update navigation bar to conditionally show:
      - Authenticated state: user indicator / link and "Sign out" (`{{ url_for('logout') }}`)
      - Unauthenticated state: "Sign in" (`{{ url_for('login') }}`) and "Get started" (`{{ url_for('register') }}`)

## Files to change

- `app.py` — Configure `app.secret_key` for session handling, update `login` route to handle `GET` and `POST` with validation and authentication, implement `logout` route to clear session and redirect
- `database/db.py` — Add `get_user_by_id` helper function
- `templates/login.html` — Use `url_for('login')` for form action and retain `email` value on failed attempts
- `templates/base.html` — Update navigation links based on user session state

## Files to create

- `tests/test_auth.py` — Pytest test suite covering login form rendering, valid login, invalid credentials, missing fields, session persistence, logout, and navbar conditional rendering

## New dependencies

No new dependencies.

## Rules for implementation

- No SQLAlchemy or ORMs
- Parameterised queries only
- Passwords hashed with werkzeug
- Use CSS variables — never hardcode hex values
- All templates extend base.html
- No DB logic inside route functions — keep all database operations in `database/db.py`
- Configure `app.secret_key` (reading from `SECRET_KEY` environment variable with a secure fallback for local development)
- Use `check_password_hash` from `werkzeug.security` to verify passwords against stored hashes
- Normalize email addresses (trim whitespace and convert to lowercase) before checking credentials
- Use generic authentication failure message (e.g., "Invalid email or password.") to avoid user enumeration
- Clear session completely on logout using `session.clear()`
- Maintain PEP 8 style and descriptive error handling

## Definition of done

- [ ] Navigating to `GET /login` displays the login form extending `base.html`
- [ ] Submitting empty email or password displays an error message and returns HTTP 400
- [ ] Submitting non-existent email displays "Invalid email or password." and returns HTTP 401
- [ ] Submitting incorrect password displays "Invalid email or password." and returns HTTP 401
- [ ] Submitting valid credentials sets `session['user_id']` and `session['user_name']` and redirects to `/` (HTTP 302)
- [ ] Form input for `email` retains its value when authentication fails, while the password field is cleared
- [ ] Authenticated users navigating to `GET /login` are redirected to `/`
- [ ] Accessing `GET /logout` clears the session and redirects to `url_for('login')` (HTTP 302)
- [ ] Navigation bar in `templates/base.html` conditionally displays "Sign out" when logged in, and "Sign in" / "Get started" when logged out
- [ ] Database helper functions in `database/db.py` use parameterized SQL queries (`?`)
- [ ] All new and existing tests pass cleanly with `pytest`
