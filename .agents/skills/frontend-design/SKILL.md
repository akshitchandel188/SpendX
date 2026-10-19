---
name: frontend-design
description: Design and build UI pages and components for Spendly, the lightweight Flask + SQLite personal expense tracker. Use this skill whenever the user asks to design, create, build, redesign, restyle or improve any Spendly screen or component — dashboard, add/edit expense form, expense list or table, profile page, stat cards, spending charts, category badges, filters, empty states, modals, navbar — even if they just say "make the profile page look good" or "UI for adding expenses" without naming the skill. Produces Jinja templates, CSS and vanilla JS that match the project's existing warm-paper / forest-green design, with clean inline SVG icons and clear usability. Do not use for backend routes, database logic or tests.
---

# Spendly UI Designer

Produces modern, production-ready UI for Spendly that looks like it was always part of
the app. The hard part isn't making something pretty — it's making something pretty
that is *consistent* with the screens already there, and that fits the project's strict
stack rules. A beautiful page in the wrong style or the wrong stack is a worse result
than a slightly plainer page that drops straight in.

## Step 1 — Inspect the existing design

Before designing or styling any page, inspect the project's real frontend files:

1. **Read these files first:**
   - `GEMINI.md` — project architecture, roadmap, and strict stack limits
   - `templates/base.html` — layout inherited by every page (navbar, fonts, footer, blocks)
   - `static/css/style.css` — design system source of truth (CSS custom properties, shared classes)
   - Existing templates (`templates/login.html`, `templates/register.html`, `templates/landing.html`) to match layout and form conventions
   - `database/db.py` — column names (`users`: `id`, `name`, `email`, `created_at`; `expenses`: `id`, `user_id`, `amount`, `category`, `date`, `description`, `created_at`) and the `CATEGORIES` list (`Food`, `Transport`, `Bills`, `Health`, `Entertainment`, `Shopping`, `Other`)
2. **Design source of truth:**
   - `static/css/style.css` defines the core tokens and styles.
   - `static/css/landing.css` has a different mint palette and white hero that predate the shared system — do not borrow styling from it.
3. **If you're redesigning something you cannot see**, or if existing visual intent is unclear, ask the user for clarification or screenshots instead of guessing.

## Step 2 — Plan the UI (keep it concise)

Decide before coding:
- The page's single primary job
- Layout structure and key visual sections
- All relevant states: default, empty state, validation errors, and disabled/submitting states
- Usability priorities: one primary action per view, labels over placeholders, the most important figure visually emphasized

## Step 3 — Build within Spendly's rules

Follow these project constraints strictly:

- **Jinja templates extend `base.html`:** Every page must start with `{% extends "base.html" %}` and fill the `title`, `head`, `content`, and optional `scripts` blocks.
- **`url_for()` for every link and asset:** Never hardcode paths like `/static/css/...` or `/login`. Always use `{{ url_for('static', filename='css/<page>.css') }}` and `{{ url_for('<endpoint>') }}`.
- **Page-specific CSS in its own file:** Put page styles in `static/css/<page>.css` and include it in the template's `{% block head %}`. Never use inline `<style>` tags.
- **Reusable classes belong in `static/css/style.css`:** If adding a truly reusable component (e.g. badge, metric card), append it to `static/css/style.css` in a clearly labeled section.
- **Reuse existing CSS classes:** Inspect `static/css/style.css` and reuse:
  - Buttons: `.btn-primary`, `.btn-ghost`, `.btn-submit`
  - Forms: `.form-group`, `label`, `.form-input`
  - Cards & Feedback: `.auth-card`, `.auth-error`
  - Typography: `var(--font-display)` (DM Serif Display), `var(--font-body)` (DM Sans)
- **Vanilla JS only:** If client-side interactivity is required, write vanilla JavaScript in `static/js/<page>.js` or append to `static/js/main.js`. No jQuery, React, npm packages, or external CDN scripts. Prefer CSS-only interactions (`<details>`, `:has()`, `:focus-visible`) and ensure the page functions with JS disabled.
- **Never modify backend routes or SQL:** UI work stops at the template boundary. Do not edit `app.py` or `database/db.py`. Document what data the template expects (see Step 4).

### Design Rules & Tokens

- **Existing design wins:** Warm paper background (`#f7f6f3`), forest-green accent (`#1a472a`), warm amber secondary (`#c17f24`), dark ink text (`#0f0f0f`), DM Serif Display for headers, and DM Sans for body text. Do not introduce neon accents, dark mode chrome, gradients, or alternative fonts.
- **Tokens only:** Always use variables defined in `static/css/style.css`:
  - Colors: `var(--paper)`, `var(--paper-warm)`, `var(--paper-card)`, `var(--ink)`, `var(--ink-soft)`, `var(--ink-muted)`, `var(--ink-faint)`, `var(--accent)`, `var(--accent-light)`, `var(--accent-2)`, `var(--accent-2-light)`, `var(--border)`, `var(--border-soft)`, `var(--danger)`, `var(--danger-light)`
  - Fonts: `var(--font-display)`, `var(--font-body)`
  - Layout & Radii: `var(--max-width)`, `var(--radius-sm)`, `var(--radius-md)`, `var(--radius-lg)`
  - If a new token is genuinely required, define it in `:root` inside `static/css/style.css` and note it.
- **Fintech-clean cards:** White cards (`var(--paper-card)`), 1px border (`var(--border)`), `var(--radius-md)`, and subtle shadows (`0 8px 40px rgba(0, 0, 0, 0.06)`).
- **8px rhythm:** Spacing in `rem` increments on an 8px grid (0.5rem = 8px, 1rem = 16px, 1.5rem = 24px, 2rem = 32px).
- **Currency formatting:** Indian Rupee symbol (`₹`). Format amounts as `₹{{ '{:,.2f}'.format(amount) }}` with tabular numbers for alignment.
- **Categories:** The 7 valid categories are `Food`, `Transport`, `Bills`, `Health`, `Entertainment`, `Shopping`, and `Other`. Display with consistent category badges combining a badge background, an icon, and a readable text label (never rely on color alone).
- **Responsive breakpoints:** Match `static/css/style.css` breakpoints (`900px` for desktop grid shifts, `600px` for mobile stack layouts).
- **Accessible by default:** Real `<label>` elements for inputs, clear `:focus-visible` outlines, touch targets at least 40px, `aria-label` on icon-only buttons, and `aria-hidden="true"` on decorative icons.
- **Destructive actions:** Expense deletions must be submitted via a `POST` form with a confirmation step rather than a bare link.

### Inline SVG Icons

Do not load external icon libraries or CDN font stylesheets. Use clean, inline SVG elements styled with `currentColor`:

- **Standard SVG attributes:**
  ```html
  <svg class="ui-icon" width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true">
      <!-- paths -->
  </svg>
  ```
- **Common SVG icon snippets for Spendly:**

  - **Plus / Add:**
    ```html
    <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true"><path d="M5 12h14"/><path d="M12 5v14"/></svg>
    ```
  - **Edit / Pencil:**
    ```html
    <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true"><path d="M17 3a2.85 2.83 0 1 1 4 4L7.5 20.5 2 22l1.5-5.5Z"/></svg>
    ```
  - **Trash / Delete:**
    ```html
    <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true"><path d="M3 6h18"/><path d="M19 6v14c0 1-1 2-2 2H7c-1 0-2-1-2-2V6"/><path d="M8 6V4c0-1 1-2 2-2h4c1 0 2 1 2 2v2"/><line x1="10" x2="10" y1="11" y2="17"/><line x1="14" x2="14" y1="11" y2="17"/></svg>
    ```
  - **Receipt / Bills:**
    ```html
    <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true"><path d="M4 2v20l2-1 2 1 2-1 2 1 2-1 2 1 2-1 2 1V2l-2 1-2-1-2 1-2-1-2 1-2-1-2 1Z"/><path d="M16 8H8"/><path d="M16 12H8"/><path d="M14 16H8"/></svg>
    ```
  - **Utensils / Food:**
    ```html
    <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true"><path d="M18 2v20"/><path d="M21 15V2a5 5 0 0 0-5 5v6c0 1.1.9 2 2 2h3Zm-11 7V2M6 2v7a2 2 0 0 1-2 2H2V2h8v9a2 2 0 0 1-2-2V2Z"/></svg>
    ```
  - **Car / Transport:**
    ```html
    <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true"><path d="M19 17h2c.6 0 1-.4 1-1v-3c0-.9-.7-1.7-1.5-1.9C18.7 10.6 16 10 16 10s-1.3-1.4-2.2-2.3c-.5-.4-1.1-.7-1.8-.7H5c-.6 0-1.1.4-1.4.9l-1.4 2.9A3.7 3.7 0 0 0 2 12v4c0 .6.4 1 1 1h2"/><circle cx="7" cy="17" r="2"/><path d="M9 17h6"/><circle cx="17" cy="17" r="2"/></svg>
    ```
  - **Shopping Bag:**
    ```html
    <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true"><path d="M6 2 3 6v14a2 2 0 0 0 2 2h14a2 2 0 0 0 2-2V6l-3-4Z"/><path d="M3 6h18"/><path d="M16 10a4 4 0 0 1-8 0"/></svg>
    ```
  - **Heart Pulse / Health:**
    ```html
    <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true"><path d="M19 14c1.49-1.46 3-3.21 3-5.5A5.5 5.5 0 0 0 16.5 3c-1.76 0-3 .5-4.5 2-1.5-1.5-2.74-2-4.5-2A5.5 5.5 0 0 0 2 8.5c0 2.3 1.5 4.05 3 5.5l7 7Z"/><path d="M3.22 12H9.5l.5-1 2 4.5 2-7 1.5 3.5h5.27"/></svg>
    ```

## Step 4 — Deliver in this structure

Deliver frontend code with clear separation of concerns:

1. **UI Structure:** Brief summary of the page layout, sections, and UX choices.
2. **Files Created / Modified:** Provide clean code in labeled blocks:
   - Template: `templates/<page>.html`
   - Stylesheet: `static/css/<page>.css` (or additions to `static/css/style.css` if creating shared components)
   - JavaScript: `static/js/<page>.js` (only if necessary)
3. **Backend Contract:** List the exact expectations for the route:
   - Expected route name and HTTP methods
   - Template context variables and types (e.g., `user: sqlite3.Row with id, name, email`, `expenses: list of rows`)
   - Form field names (`name` attributes) for POST requests
4. **Design Notes:** Mention any new reusable utility classes or token adjustments made.

## What to Avoid

- Do not introduce CSS frameworks (Bootstrap, Tailwind) or JavaScript frameworks (React, Vue).
- Do not use external CDN libraries, Google Fonts icon sets, or third-party chart libraries.
- Do not use inline `<style>` tags or unorganized inline styling.
- Do not invent data schema fields that do not exist in `database/db.py`.
- Do not modify backend code (`app.py`, `database/db.py`) or database schema.
- Do not redesign the navigation bar or footer inside individual templates — those are defined centrally in `templates/base.html`.