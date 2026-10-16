# Spec: Registration

## Overview

Enable new users to create an account by submitting their full name, email address, and password. This feature completes Step 2 of the Spendly roadmap, establishing the core user identity and account creation workflow that subsequent authentication, session management, and user-isolated expense tracking depend upon.

## Depends on

Step 01 (Database Setup) — requires `spendly.db` SQLite schema, the `users` table, and the `get_db()` helper in `database/db.py`.

## Routes

- `GET /register` — Renders the registration form page (`register.html`) — public
- `POST /register` — Validates user registration input, verifies email uniqueness, hashes the password, creates the user record in SQLite via `database/db.py`, and redirects to `/login` — public

## Database changes

No database changes.

The `users` table schema already exists with the necessary columns (`id`, `name`, `email`, `password_hash`, `created_at`). New user data access helpers must be added to `database/db.py`:
- `get_user_by_email(email, db_path=None)` — Look up existing user by normalized email
- `create_user(name, email, password, db_path=None)` — Hash password with werkzeug and insert new user record using parameterized SQL

## Templates

- **Create:** None
- **Modify:** `templates/register.html`
  - Update `<form>` action to `{{ url_for('register') }}` instead of hardcoded `/register`
  - Ensure error message container renders when `error` is passed from the route
  - Preserve submitted `name` and `email` values on validation errors (`value="{{ name or '' }}"`, `value="{{ email or '' }}"`)

## Files to change

- `app.py` — Update `register` route to handle both `GET` and `POST`, perform input validation, call `database/db.py` helper functions, and handle redirects
- `database/db.py` — Add `get_user_by_email` and `create_user` helper functions
- `templates/register.html` — Use `url_for('register')` and preserve entered field values on validation errors

## Files to create

- `tests/test_register.py` — Pytest test suite covering registration page rendering, valid account creation, password hashing, and validation error cases

## New dependencies

No new dependencies.

## Rules for implementation

- No SQLAlchemy or ORMs
- Parameterised queries only
- Passwords hashed with werkzeug
- Use CSS variables — never hardcode hex values
- All templates extend `base.html`
- No DB logic inside route functions — keep all database operations in `database/db.py`
- Normalize email addresses (trim whitespace and convert to lowercase) before checking and storing
- Form validation: full name required, valid email format, minimum password length of 8 characters
- Maintain PEP 8 style and descriptive error handling

## Definition of done

- [ ] Navigating to `GET /register` displays the registration form extending `base.html`
- [ ] Submitting empty required fields displays an informative error message and returns HTTP 400
- [ ] Submitting a password with fewer than 8 characters displays an error message
- [ ] Submitting an invalid email address displays an error message
- [ ] Submitting an email that is already registered displays an error message indicating the email is taken
- [ ] Entering valid information creates a new record in `users` with a securely hashed password
- [ ] Plain text passwords are never stored in the database
- [ ] Successful registration redirects the user to the `/login` route (`url_for('login')`)
- [ ] Form inputs for `name` and `email` retain their values when an error occurs
- [ ] Database helper functions in `database/db.py` use parameterized SQL queries (`?`)
- [ ] All new and existing tests in `tests/test_register.py` and `tests/test_db.py` pass cleanly with `pytest`
