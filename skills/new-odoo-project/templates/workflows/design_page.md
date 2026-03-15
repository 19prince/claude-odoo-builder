# Design Page Workflow

## Objective
Design a new Odoo website page that is visually polished and ready to push directly to Odoo's WYSIWYG editor. The output is a validated HTML file in `.tmp/` that Claude can push with one command.

## Required Inputs
Collect these from the user before starting. Ask if not provided:
- **Page name** — human-readable (e.g., "About Us")
- **Page URL slug** — the path (e.g., `/about`)
- **Design brief** — purpose, tone, key sections needed, any references
- **Brand colors** (optional) — hex values or "use Odoo theme defaults"
- **Odoo version** — 15, 16, or 17 (affects Bootstrap version: BS4 vs BS5)

---

## Step 1: Orient with Existing Pages

```bash
python3 tools/list_pages.py
```

- Review output. If a page already exists at the target URL, switch to the update path in `workflows/push_to_odoo.md`.
- If a similar page exists (e.g., already have `/about`, user wants `/about-team`), fetch the existing one for structural reference:
  ```bash
  python3 tools/get_page.py --url /about
  ```

---

## Step 2: Load the Design System

Read `workflows/design_system.md` in full before writing any HTML.

Key things to internalize:
- Bootstrap version for this Odoo install
- Which paste-ready section templates match the requested sections
- `o_editable` class convention — every content region needs it
- QWeb wrapper format — required for the arch

---

## Step 3: Plan the Page Structure

Decide which sections the page needs. Map the user's brief to section templates:

| User request | Template to use |
|---|---|
| "hero with headline + CTA" | Hero Section |
| "our services / features" | Three-Column Feature Grid |
| "about us story" | Split Content (image + text) |
| "contact / get in touch" | CTA Section or Contact Form Section |
| "testimonials / reviews" | Testimonials Row |
| "pricing" | Pricing Table |
| "team members" | Three-Column grid (use person card variant) |

Aim for 3–5 sections per page. More than 6 makes pages feel overwhelming.

---

## Step 4: Write the HTML

Use the paste-ready templates from `design_system.md` as starting points. Customise:
- Headlines and body copy to match the user's brief
- Colors: swap `bg-dark`, `bg-primary`, etc. to match brand
- Replace placeholder images with real image URLs if provided, or keep `placehold.co` URLs

**Structure rules:**
- Each section is a `<section>` element
- Every section must have `o_colored_level` class (enables Odoo's background color picker)
- Every editable text container must have `o_editable` class
- All images must have `img-fluid` class
- Use `container` (not `container-fluid`) unless user wants full-bleed layout
- Standard vertical rhythm: `py-5` on `<section>`
- Do NOT include `<html>`, `<head>`, or `<body>` — arch is inner template content only
- Do NOT include `<t t-name=...>` wrapper — `push_page.py` adds it automatically

**Save the draft:**
```
.tmp/draft_{slug}.html
```
where `{slug}` is the URL without slashes (e.g., `draft_about.html`).

---

## Step 5: Validate

```bash
python3 tools/validate_html.py --input .tmp/draft_{slug}.html
```

- Fix all ERRORs before proceeding (unclosed tags, disallowed root elements)
- Review WARNINGs — at minimum, ensure `o_editable` is present on all text blocks
- Re-run until you get: `Validation PASSED`

---

## Step 6: Present to User

Show the user the HTML draft and ask for approval or revision requests. Options:
- Approved → proceed to Step 7
- Changes requested → edit the draft file and re-validate, then re-present
- Wants to see it live first → push as unpublished (Step 7), user previews via Odoo backend

---

## Step 7: Push to Odoo

Follow `workflows/push_to_odoo.md` with:
- `--create` (new page) or `--update` (existing page)
- `--name` = the page name
- `--url` = the page URL slug
- `--file` = `.tmp/draft_{slug}.html`

---

## Output
- Validated HTML draft saved to `.tmp/draft_{slug}.html`
- Page live (or staging as unpublished) on Odoo
- User can open Odoo website editor for WYSIWYG final tweaks

---

## Edge Cases

| Situation | Resolution |
|---|---|
| Odoo rejects the arch | Run validate_html.py, look for unclosed QWeb `<t>` tags or invalid XML characters |
| User wants custom CSS | Add a `<style>` block at top of draft, OR scaffold a snippet module for scoped CSS |
| Page URL already taken | Switch to `--update` mode; backup is created automatically |
| User has custom fonts | Add `font-family` in a `<style>` block referencing the font import URL |
| Odoo 15 (Bootstrap 4) | Avoid BS5-only utilities: `gap-*`, `d-grid`, `fs-*`. Use `mt-`, `gutter-`, `font-size` instead |
| User wants animation | Use Bootstrap's `animate__` classes or add a simple `<style>` with CSS keyframe animation |

---

## Notes
- Odoo's editor strips `<script>` tags from page arch — use `scaffold_snippet.py` for JS behavior
- The `o_colored_level` class on `<section>` enables the background color picker in the editor sidebar
- Multiple instances of the same section type are fine — just ensure unique IDs are avoided (use classes only)
- After pushing, encourage the user to click through the page in Odoo's editor to verify all regions are editable
