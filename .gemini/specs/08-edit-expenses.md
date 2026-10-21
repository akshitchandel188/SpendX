# Spec: Edit Expenses

## Overview

Step 8 allows authenticated users to edit and update their existing logged expenses through a dedicated form page at `/expenses/<int:id>/edit`. The route currently exists as a placeholder stub; this step upgrades it to a full `GET` and `POST` handler, pre-populating an edit form with the expense's current values, validating user inputs (positive amount, valid category from the 7 standard categories, valid date, and optional description up to 200 characters), ensuring strict user authorization (users can only view and update their own expenses; accessing another user's expense or a non-existent expense returns a 404), persisting changes to the database, and redirecting back to `/profile` on success. An "Edit" action link is also integrated into each transaction row in the recent transactions table on `profile.html`.

## Depends on

- Step 01 (Database Setup) — SQLite database schema, `expenses` table, and `get_db()` helper in `database/db.py`
- Step 03 (Login and Logout) — User authentication and session management (`session["user_id"]`)
- Step 05 (Backend Routes for Profile Page) — Profile dashboard view, user helpers, and recent transaction listings
- Step 07 (Add Expenses) — Expense validation conventions, `CATEGORIES` constant, and date input handling

## Routes

- `GET /expenses/<int:id>/edit` — render the edit expense form pre-filled with the existing expense details — logged-in
- `POST /expenses/<int:id>/edit` — validate input, update the expense record in the database, and redirect to `/profile` — logged-in

## Database changes

No database changes.

The `expenses` table already contains all required columns: `id`, `user_id`, `amount`, `category`, `date`, `description`, `created_at`.

New query helpers to add in `database/queries/transactions.py` (and re-exported in `database/queries.py`):
- `get_expense_by_id(expense_id, user_id=None, db_path=None)` — fetches an expense by ID, optionally verifying ownership by `user_id`. Returns a dictionary of expense data or `None`.
- `update_expense(expense_id, user_id, amount, category, date, description=None, db_path=None)` — updates the specified expense record matching `id` and `user_id` using parameterized SQL. Returns `True` if updated, `False` otherwise.

## Templates

- **Create**:
  - `templates/edit_expense.html`
    - Extends `base.html`
    - Form with `method="POST"` and action `{{ url_for('edit_expense', id=expense.id) }}`
    - Fields:
      - `amount` — number input, `step="0.01"`, `min="0.01"`, required, pre-filled with current expense amount
      - `category` — `<select>` dropdown with the 7 fixed categories, with current expense category selected
      - `date` — `<input type="date">`, required, pre-filled with current expense date (`YYYY-MM-DD`)
      - `description` — text input, optional, `maxlength="200"`, pre-filled with current expense description
    - Form action buttons: "Save Changes" submit button and a "Cancel" link pointing back to `url_for('profile')`
    - Error container displaying validation messages when errors occur, preserving modified inputs
- **Modify**:
  - `templates/profile.html`
    - Add an "Actions" column (or an Edit link) to the recent transactions table so users can easily edit any listed expense

## Files to change

- `app.py` — Replace the placeholder at `/expenses/<int:id>/edit` with full `GET` and `POST` handlers:
  - Ensure user is logged in (redirect to `url_for('login')` if not authenticated)
  - Verify expense exists and belongs to `session["user_id"]` (abort 404 if not found or unauthorized)
  - GET: render `edit_expense.html` populated with the current expense data
  - POST: validate submitted data, call `update_expense`, and redirect to `url_for('profile')` on success; re-render on validation error
- `database/queries/transactions.py` — Implement `get_expense_by_id` and `update_expense` query helpers
- `database/queries.py` — Re-export `get_expense_by_id` and `update_expense`
- `templates/profile.html` — Add an "Actions" column header and an "Edit" link in each table row linking to `url_for('edit_expense', id=exp.id)`

## Files to create

- `templates/edit_expense.html` — The edit expense form template
- `static/css/edit_expense.css` — Stylesheet for the edit expense view consistent with the warm-paper / forest-green design
- `tests/test_edit_expense.py` — Pytest test suite covering route access, authorization, form validation, updates, and database persistence

## New dependencies

No new dependencies.

## Rules for implementation

- No SQLAlchemy or ORMs — raw `sqlite3` only via `get_db()`
- Parameterised queries only (`?` placeholders) — never string interpolation or f-strings in SQL
- Passwords hashed with werkzeug
- Use CSS variables — never hardcode hex values
- All templates extend `base.html`
- Strict user authorization: users must only be able to view and edit expenses they own. Accessing another user's expense or a non-existent expense ID must trigger `abort(404)`.
- Unauthenticated access to both `GET` and `POST` `/expenses/<int:id>/edit` must redirect to `url_for('login')`.
- Validation rules for `POST`:
  - `amount`: required, must be a positive number greater than 0 (convert with `float()`; handle `ValueError`)
  - `category`: required, must be one of the 7 predefined categories: Food, Transport, Bills, Health, Entertainment, Shopping, Other
  - `date`: required, must be a valid date in `YYYY-MM-DD` format
  - `description`: optional; strip whitespace; store `None` (NULL) if blank; maximum length 200 characters
  - On any validation error, re-render the form with an appropriate error message while retaining the submitted values
- After successful update, redirect to `url_for('profile')`
- Currency must always display as ₹ — never £ or $
- No inline styles

## Definition of done

- [ ] Visiting `/expenses/<id>/edit` while logged out redirects to `/login`
- [ ] Visiting `/expenses/<id>/edit` with a non-existent expense ID returns a 404 error
- [ ] Visiting `/expenses/<id>/edit` for an expense owned by another user returns a 404 error
- [ ] Visiting `/expenses/<id>/edit` for an owned expense displays the edit form with amount, category, date, and description pre-populated
- [ ] The category dropdown contains all 7 categories with the expense's current category selected
- [ ] Submitting valid updates updates the expense in the database and redirects to `/profile`
- [ ] The updated expense appears with its new values in the profile transaction list and updates summary stats
- [ ] Submitting with missing, zero, or negative amount re-renders the form with an error and preserves entered values
- [ ] Submitting with an invalid category re-renders the form with an error
- [ ] Submitting with an invalid date re-renders the form with an error
- [ ] Submitting with a description exceeding 200 characters re-renders the form with an error
- [ ] Submitting with an empty description saves the expense with `description = NULL`
- [ ] The "Edit" link in the recent transactions table on `/profile` navigates to `/expenses/<id>/edit`
- [ ] Clicking "Cancel" navigates back to `/profile` without applying changes
- [ ] All unit and route tests in `tests/test_edit_expense.py` pass cleanly
