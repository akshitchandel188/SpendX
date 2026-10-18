# Implementation Plan: Login and Logout (Step 03)

## 1. Overview and Objectives

This plan outlines the implementation for **Step 03: Login and Logout** of the Spendly personal expense tracker based on `.gemini/specs/03-login-logout.md`.

The goal is to enable registered users to log in securely with their email and password, manage authenticated state through Flask session cookies, update the navigation layout dynamically based on authentication status, and allow users to sign out cleanly.

All work strictly adheres to the constraints in `GEMINI.md`:
- Flask session cookies with a configurable secret key (no heavy auth frameworks or external stores).
- SQLite access confined to `database/db.py` with parameterized queries only.
- Passwords verified with Werkzeug's `check_password_hash`.
- No new pip dependencies.
- Vanilla HTML/CSS extending `base.html` using existing design tokens.

---

## 2. Prerequisites & Architecture Verification

- **Step 01 (Database Setup)**: Completed. The `users` table exists in `spendly.db` with `id`, `name`, `email`, `password_hash`, `created_at`.
- **Step 02 (Registration)**: Completed. `get_user_by_email` and `create_user` are implemented in `database/db.py`.
- **Roadmap check**: In `GEMINI.md`, `GET /logout` is currently marked as `Stub — Step 3`. `GET /login` currently only renders the template without POST credential handling or session establishment.

---

## 3. Detailed Component Plan

### 3.1. Database Helper (`database/db.py`)
Add helper function to retrieve user records by primary key ID:
```python
def get_user_by_id(user_id, db_path=None):
    """
    Look up user by primary key ID from session data.
    Returns sqlite3.Row if found, otherwise None.
    """
```
- Validate `user_id`: If `user_id is None`, return `None` immediately.
- Execute parameterized query `SELECT * FROM users WHERE id = ?;` with parameter `(user_id,)`.
- Ensure connection is closed cleanly in a `try...finally` block.

### 3.2. App Configuration & Session Setup (`app.py`)
- Import `os` and `session` from Flask.
- Import `check_password_hash` from `werkzeug.security`.
- Import `get_user_by_id` from `database.db`.
- Configure `app.secret_key`:
  ```python
  app.secret_key = os.environ.get("SECRET_KEY", "dev-secret-key-spendly-fallback")
  ```

### 3.3. Route Handlers (`app.py`)

#### `GET /login`
- Check if user is already authenticated (`session.get("user_id")`).
- If authenticated: redirect to `url_for("landing")` (HTTP 302).
- If unauthenticated: render `login.html` (HTTP 200).

#### `POST /login`
1. Extract and sanitize input:
   - `email = request.form.get("email", "").strip().lower()`
   - `password = request.form.get("password", "")`
2. Validate required fields:
   - If either `email` or `password` is missing/empty:
     - Return `login.html` with `error="All fields are required."` and `email=email` (HTTP 400).
3. Query database via `get_user_by_email(email)`:
   - If user does not exist OR `not check_password_hash(user["password_hash"], password)`:
     - Return `login.html` with generic error `error="Invalid email or password."` and `email=email` (HTTP 401).
     - Note: Using a single generic message prevents email enumeration.
4. On successful authentication:
   - Set session attributes:
     - `session["user_id"] = user["id"]`
     - `session["user_name"] = user["name"]`
   - Redirect to `url_for("landing")` (HTTP 302).

#### `GET /logout`
- Call `session.clear()`.
- Redirect to `url_for("login")` (HTTP 302).

### 3.4. Templates

#### `templates/login.html`
- Form action: replace hardcoded `action="/login"` with `action="{{ url_for('login') }}"`.
- Email input field: add `value="{{ email or '' }}"` to preserve submitted input on error.
- Password input field: keep value empty on error for security.
- Preserve existing `auth-error` banner rendering (`{% if error %}<div class="auth-error">{{ error }}</div>{% endif %}`).

#### `templates/base.html`
- Update `.nav-links` container to conditionally render based on `session.get('user_id')`:
  - **Authenticated (`session.get('user_id')`)**:
    - Display user identifier: `<span class="nav-user">{{ session.get('user_name') }}</span>`
    - Display logout link: `<a href="{{ url_for('logout') }}">Sign out</a>`
  - **Unauthenticated**:
    - Display login link: `<a href="{{ url_for('login') }}">Sign in</a>`
    - Display register CTA: `<a href="{{ url_for('register') }}" class="nav-cta">Get started</a>`

---

## 4. Test Strategy

### 4.1. Unit Tests (`tests/test_db.py`)
Add tests for `get_user_by_id`:
- Retrieve an existing user by valid ID -> returns correct `sqlite3.Row` matching name and email.
- Query non-existent ID (e.g. `99999`) -> returns `None`.
- Query `None` as ID -> returns `None` without executing invalid SQL.

### 4.2. Auth & Session Integration Tests (`tests/test_auth.py`)
Create a comprehensive test suite using pytest and the Flask test client:
1. `test_login_get_renders_form`: Verifies GET `/login` returns 200, contains form fields, and `action="{{ url_for('login') }}"`.
2. `test_login_already_authenticated_redirects`: Verifies that a client with active session (`user_id`) is redirected to `/` on GET `/login`.
3. `test_login_missing_email_or_password_returns_400`: Verifies missing inputs return 400 and appropriate error message.
4. `test_login_nonexistent_email_returns_401`: Verifies unregistered email returns 401 and generic error message.
5. `test_login_wrong_password_returns_401`: Verifies incorrect password returns 401, error message, and retains email input value while omitting password.
6. `test_login_success_sets_session_and_redirects`: Verifies valid credentials set `session['user_id']` and `session['user_name']` and issue 302 redirect.
7. `test_login_email_case_insensitivity`: Verifies that user can log in with mixed-cased email.
8. `test_logout_clears_session_and_redirects`: Verifies GET `/logout` wipes session keys and redirects to `/login`.
9. `test_navbar_unauthenticated_links`: Verifies navbar displays "Sign in" and "Get started" when logged out.
10. `test_navbar_authenticated_links`: Verifies navbar displays user name and "Sign out" when logged in.

---

## 5. Step-by-Step Implementation Sequence

1. **Step 1: Database helper `get_user_by_id`**
   - Add `get_user_by_id` in `database/db.py`.
   - Update `tests/test_db.py` with test cases and verify with `pytest tests/test_db.py`.

2. **Step 2: Session configuration in `app.py`**
   - Import `os`, `session`, `check_password_hash`, and `get_user_by_id`.
   - Set `app.secret_key`.

3. **Step 3: Route handlers in `app.py`**
   - Implement `GET /login` with authenticated redirect check.
   - Implement `POST /login` with field validation, hash verification, session setup, and error handling.
   - Implement `GET /logout` with session clearance and redirect.

4. **Step 4: Template refinements**
   - Update `templates/login.html` (dynamic URL action, email value persistence).
   - Update `templates/base.html` (conditional navbar elements).

5. **Step 5: Test suite implementation**
   - Create `tests/test_auth.py` covering all positive and negative authentication flows.

6. **Step 6: Verification & regression testing**
   - Run full test suite with `pytest` to guarantee all tests (registration, DB, auth) pass cleanly.
   - Run a subagent to verify test results as required by `GEMINI.md`.

---

## 6. Definition of Done & Verification Checklist

- [ ] `get_user_by_id` implemented in `database/db.py` using parameterized query `?`.
- [ ] `app.secret_key` properly configured in `app.py`.
- [ ] `GET /login` displays login form when unauthenticated.
- [ ] `GET /login` redirects authenticated users to `/`.
- [ ] `POST /login` with empty fields returns HTTP 400 and preserves email.
- [ ] `POST /login` with non-existent email returns HTTP 401 and generic error.
- [ ] `POST /login` with incorrect password returns HTTP 401, preserves email, and clears password field.
- [ ] `POST /login` with valid credentials sets `session['user_id']` and `session['user_name']` and redirects to `/` (HTTP 302).
- [ ] `GET /logout` completely clears session and redirects to `url_for('login')` (HTTP 302).
- [ ] `templates/base.html` conditionally renders "Sign out" and username when logged in; "Sign in" and "Get started" when logged out.
- [ ] No inline database queries in routes; all queries in `database/db.py`.
- [ ] Full test suite (`pytest`) passes without errors.
