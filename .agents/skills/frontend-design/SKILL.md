---
name: frontend-design
description: Design and build UI pages and components for SpendX (also called Spendly), the Flask + Jinja personal expense tracker at github.com/akshitchandel188/SpendX. Use this skill whenever the user asks to design, create, build, redesign, restyle or improve any SpendX/Spendly screen or component — dashboard, add/edit expense form, expense list or table, profile page, stat cards, spending charts, category badges, filters, empty states, modals, navbar — even if they just say "make the profile page look good" or "UI for adding expenses" without naming the skill. Produces Jinja templates, CSS and vanilla JS that match the project's existing warm-paper / forest-green design, with inline Lucide icons and clear usability. Do not use for backend routes, database logic or tests.
---

# SpendX UI Designer

Produces modern, production-ready UI for SpendX that looks like it was always part of
the app. The hard part isn't making something pretty — it's making something pretty
that is *consistent* with the screens already there, and that fits the project's strict
stack rules. A beautiful page in the wrong style or the wrong stack is a worse result
than a slightly plainer page that drops straight in.

## Step 1 — Ground yourself in the real design

1. **Find the repo.** Look in the working directory first, then use a path the user
   gave. If neither exists, `git clone --depth 1 https://github.com/akshitchandel188/SpendX.git /tmp/SpendX`.
2. **Read these files before designing anything:**
   - `GEMINI.md` — the project's rules (stack limits, where files go)
   - `templates/base.html` — what every page inherits (navbar, fonts, blocks)
   - `static/css/style.css` — tokens and shared classes (source of truth)
   - the existing template closest to what you're building (e.g. `login.html` for any form)
   - `database/db.py` — the real columns and the `CATEGORIES` list, so mock data and
     field names are real
3. **If the repo is unreachable**, work from `references/design-system.md` (a snapshot)
   and say you did.
4. **If you're redesigning something you can't see**, or the existing look is unclear,
   ask the user for screenshots instead of guessing. Guessing is how consistency breaks.

`style.css` is the design source of truth. `landing.css` has a different mint palette
and white hero that predate the shared system — don't borrow from it.

## Step 2 — Plan the UI (keep it short)

Decide before coding: the page's single main job, the layout and key sections, which
states exist (empty, error, loading/disabled, success), and the 2–3 UX decisions that
matter (e.g. "amount field first and autofocused — it's the thing people came to enter").
Anchor on usability and clarity: one primary action per view, labels over placeholders,
the most important number biggest.

## Step 3 — Build within the project's rules

These come from `GEMINI.md`; each has a reason, so don't bend them even when a shortcut
looks tempting:

- **Jinja templates that `{% extends "base.html" %}`** and fill `title` / `content` /
  `head` / `scripts` blocks. Every page shares the navbar and footer this way.
- **`url_for()` for every internal link and asset.** Hardcoded paths break when routes move.
- **Page-specific CSS in its own file** (`static/css/<page>.css`, linked from the
  `head` block). No inline `<style>` tags. Truly reusable components (card, badge, stat
  card…) go in `style.css` as a new labelled section.
- **Vanilla JS only**, in `static/js/<page>.js` or `main.js`. No React, jQuery, npm
  packages, CDN libraries or chart libraries. Prefer CSS-only solutions (`<details>`,
  `:has()`, `:focus-visible`) and progressive enhancement: the page must work with JS off.
- **Reuse existing classes** (`.btn-primary`, `.btn-ghost`, `.form-group`, `.form-input`,
  `.auth-error`, …) instead of redefining them. See `references/design-system.md` §4.
- **Never touch routes or SQL.** UI work ends at the template boundary. Instead of
  writing backend code, list what the template expects (see output format).

### Design rules

- **Existing design wins.** Keep the warm paper background, forest-green accent, amber
  secondary, DM Serif Display for headings and big numbers, DM Sans for everything else.
  "Modern SaaS" here means better hierarchy, spacing and states *within* these tokens —
  not a new palette, new fonts, gradients or dark chrome.
- **Tokens only.** `var(--accent)`, `var(--border)`, `var(--radius-md)`… A raw hex means a
  token is missing — add a token (and mention it) rather than hardcoding.
- **Card-based, quiet, fintech-clean.** White cards, 1px border, `--radius-md`,
  barely-there shadow. Generous whitespace; group with space and borders before colour.
- **8px rhythm.** Spacing in `rem` steps on a 0.5rem grid (0.25rem for tight gaps).
- **Hierarchy:** one display-serif element per view (the page title or the key total),
  then 500/600-weight DM Sans for emphasis, muted ink for metadata.
- **Currency is ₹.** Format as `₹{{ '{:,.2f}'.format(amount) }}`, tabular numerals in
  lists. Money should be the easiest thing on screen to read.
- **Categories** get a consistent colour + icon + visible name (never colour alone); see
  `references/design-system.md` §5.
- **Responsive and mobile-first.** Breakpoints 900px and 600px, matching `style.css`.
  Forms especially — people add expenses on their phones.
- **Form actions:** primary action first and full-width on mobile, with the secondary
  (Cancel) below it; inline on desktop. Hide number spinners on money fields.
- **Accessible by default:** real `<label>`s, `:focus-visible` rings, 40px+ touch
  targets, `aria-label` on icon-only buttons, decorative icons `aria-hidden`, sufficient
  contrast on tinted backgrounds.
- **Destructive actions** (delete) use a `POST` form with a confirmation step — never a
  bare link. Note that the current `delete_expense` placeholder is a GET route; flag it.
- **Design the states, not just the happy path:** empty, validation error (reuse the
  `error` / `.auth-error` pattern the auth pages use), and long text / large amounts.

### Icons — inline Lucide via the bundled macro

Copy `assets/_icons.html` to `templates/_icons.html` (if it isn't there), then:

```jinja
{% from "_icons.html" import icon %}
{{ icon("wallet") }}                                  {# decorative #}
{{ icon("trash-2", size=18, label="Delete expense") }} {# meaningful #}

{% from "_icons.html" import category_icon %}
{{ category_icon(expense.category) }}                 {# right icon for any of the 7 categories #}
```

It contains ~40 real Lucide icons (wallet, receipt, indian-rupee, utensils, car,
heart-pulse, film, shopping-bag, plus, pencil, trash-2, search, funnel, calendar,
trending-up/down, chart-pie, circle-alert, circle-check, and more). If you need one
that's missing, add its inner shapes to the `ICONS` dict from lucide.dev — no library,
no CDN. Use icons to aid scanning (category, action, status), not as decoration: if an
icon doesn't help someone find or understand something, drop it.

## Step 4 — Respond in this shape

Keep the explanation brief; the code is the deliverable.

1. **UI structure** — a few lines: layout, key sections, important UX decisions.
2. **Files** — each in its own fenced block with its path as the label, in this order:
   template(s) → `static/css/...` (and any addition to `style.css`, clearly marked as an
   append) → JS only if actually needed. Modular, commented sparingly, no boilerplate
   dumps. Where the user can run it, write the files into the repo; otherwise present
   them in chat.
3. **Backend needs** — one short list of what the template expects: route name, template
   context variables and their shape (e.g. `expenses: list of rows with id, amount,
   category, date, description`), and form field names. Don't implement it unless asked.
4. **Notes** — only if relevant: new tokens added, `base.html` or `style.css` changes, or
   anything you assumed.

For tiny requests ("make this button look better") skip the ceremony: show the change,
one line on why.

## Avoid

- A generic "dashboard template" look: purple gradients, glassmorphism, neon, stock
  hero illustrations, a different font stack.
- Unstructured code dumps — one giant file, inline styles, repeated one-off classes.
- Inventing data fields the schema doesn't have (expenses are `amount`, `category`,
  `date`, `description`, owned by a `user_id`).
- Adding dependencies, even "just a small CDN script".
- Redesigning the navbar/footer when asked for a page — those live in `base.html`.