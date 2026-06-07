# Migrate Staging to Production Workflow

## Objective

Transfer all design and content changes from the staging Odoo instance to the production instance without data loss or downtime. Covers: CSS theme views, page arch (HTML content), footer, and page meta fields.

The migration script (`tools/migrate_to_production.py`) handles the mechanics. This workflow defines the questions to ask, checks to run, and decisions to make before and after running it.

---

## When to Use This

- After completing a round of design/content work on staging
- Before any major launch or release
- When production and staging have diverged and staging is the source of truth

---

## Questions to Ask Before Starting

These must be answered before writing or running any migration code. Ask the user directly if any are unclear.

### 1. What changed on staging?

Enumerate every category of change so nothing is missed:

- [ ] Page arch (HTML content) — which pages? (e.g., `/`, `/about`)
- [ ] CSS theme views (inherited views) — new views added? existing views updated?
- [ ] Footer arch
- [ ] Meta titles / meta descriptions — which pages were updated?
- [ ] New pages created on staging that don't exist yet on production?
- [ ] Blog posts or blog settings changed?
- [ ] Any Odoo settings changed (website name, favicon, colors, fonts in Odoo editor)?

### 2. Does production have the same pages?

Confirm that every page URL being migrated exists on production. If a page was created on staging but not yet on production:
- Use `tools/push_page.py --create` to create it first
- Then include it in the migration

### 3. Are the same Odoo modules installed on production?

Key modules this project depends on:
- `website` (core)
- `website_blog` — required for blog listing/article CSS views
- Any custom modules (e.g., ICP module) — if a page view doesn't exist on production, the CSS inherit will fail

Ask: "Is the [module name] installed on production?" before creating any CSS view that inherits from it.

### 4. Do the production page URLs match staging exactly?

URL mismatches are the most common failure. If a page URL was renamed on staging, confirm whether production has been updated too or if the old URL is still live.

### 5. Should meta descriptions be overwritten if they already exist on production?

Current behavior: the script always writes meta fields regardless of existing values. If production has manually curated meta that should be preserved, exclude those pages or review them first with:

```bash
python3 -c "
import sys; sys.path.insert(0, 'tools')
from odoo_client import OdooClient
c = OdooClient()
pages = c.search_read('website.page', [('active','=',True)], ['url','website_meta_title','website_meta_description'])
for p in sorted(pages, key=lambda x: x['url']):
    print(p['url'], '|', p['website_meta_title'] or '(none)')
"
```

### 6. Leave homepage meta as-is?

The homepage meta title/description is usually set manually in the Odoo backend and may differ intentionally on production. Confirm before including it in `META_UPDATES`.

### 7. Are production credentials ready?

The script reads from `.env`. Before running:
- Confirm `.env` has been updated with `ODOO_URL`, `ODOO_DB`, `ODOO_USER`, `ODOO_PASSWORD` pointing to **production**
- Staging credentials should be saved elsewhere (e.g., `.env.staging`) before overwriting

---

## Pre-Flight Checklist

Run these before executing the migration:

### Verify `.env` points to production
```bash
head -4 .env
```
Confirm the URL matches the production domain, not staging.

### Run dry-run first — always
```bash
python3 tools/migrate_to_production.py --dry-run
```
Review the output line by line. Expected output for each step:
- `WOULD UPDATE` — view/page found, arch would be written
- `WOULD CREATE` — view not yet on production, would be created
- `SKIP` — page or parent view not found; investigate before proceeding

Any `SKIP` that shouldn't be a skip means either a URL mismatch, missing module, or wrong view key. Fix before running live.

### Confirm no unsaved staging work
Make sure all staging edits have been saved to `.tmp/` files. The migration pushes from local files, not directly from staging.

---

## Running the Migration

```bash
python3 tools/migrate_to_production.py
```

The script runs all steps in sequence and prints the result of each. Expected output per step:
- `UPDATED view ID {n} (...)` — success
- `CREATED view ID {n} (...)` — success (new view)
- `SKIP` — see troubleshooting section

---

## Adding New Items to the Migration Script

When new pages or CSS views are added to staging, update `tools/migrate_to_production.py`:

### New page arch
Add a `migrate_page_arch()` call in `main()`:
```python
print("\nN. My new page")
migrate_page_arch(client, url="/my-page", html_file=os.path.join(TMP, "draft_my_page.html"), dry_run=dry_run)
```
Save the page arch to `.tmp/draft_my_page.html` first.

### New CSS theme view
Add a `migrate_css_view()` call:
```python
print("\nN. My page theme")
migrate_css_view(
    client,
    xml_file=os.path.join(TMP, "my_page_theme.xml"),
    view_key="website.acme_my_page_theme",
    view_name="Acme My Page Theme",
    inherit_key="website.layout",   # or "website_blog.blog_post_short", etc.
    dry_run=dry_run,
)
```
Save the CSS XML to `.tmp/my_page_theme.xml` in the format used by the other `.xml` files in `.tmp/`.

### New meta descriptions
Append to `META_UPDATES` at the top of the script:
```python
{
    "url": "/my-page",
    "title": "My Page | Acme Corp",
    "description": "...",
},
```

---

## Key Technical Notes

### Why we use `ir.ui.view` inherit for CSS, not page arch
Injecting CSS via an inherited view (rather than embedding it in the page arch) means the page content is never touched. This is critical because:
- Pages can be edited in the Odoo website editor without the CSS disappearing
- The same CSS applies even if the page arch is republished via the editor

### The navbar backdrop-filter constraint
The global CSS sets `body { background: #071222 }` (dark). This is intentional. The navbar uses `backdrop-filter: blur(10px)`, which blurs whatever color is visually behind it. If `body` were white, the navbar would appear light/grey. On pages with white content, **individual sections** get explicit `background: #ffffff` — not `body`.

Never set `body { background: #ffffff }` globally. Always give white sections explicit backgrounds instead.

### View keys — how to find the right one
Every Odoo view has a `key` field (e.g., `website.layout`, `website_blog.blog_post_short`). To find the key for any view:
```python
views = c.search_read("ir.ui.view", [("name", "ilike", "blog post")], ["id", "key", "name"])
```
Or by URL — find the page, read its `view_id`, then read the view's `key`.

### Arch format for inherited views
CSS inject views are stored with this arch structure:
```xml
<data>
  <xpath expr="//head" position="inside">
    <style>/* your CSS */</style>
  </xpath>
</data>
```
The `inherit_id` and `name` attributes that appear in `.tmp/*.xml` files are module-data conventions — they are stripped by the migration script before writing to the DB. The numeric `inherit_id` is set as a record field, not inside the arch.

### QWeb arch wrapping for page content
Page arches must be wrapped in:
```xml
<t t-name="website.page_{slug}">
  <t t-call="website.layout">
    {page content}
  </t>
</t>
```
`push_page.py` and `migrate_to_production.py` both handle this automatically. If the file already starts with `<t t-name=`, the wrapper is skipped.

---

## Post-Migration Verification

After running the migration, ask the user to check each of the following:

### Pages
- [ ] Homepage (`/`) — layout, fonts, hero, services, testimonials, CTA section
- [ ] About (`/about`) — same design as staging
- [ ] Blog listing (`/blog`) — dark background, white cards, dark text on cards
- [ ] Any blog article — dark header, white body, readable text
- [ ] ICP page (`/odoo-icp-module`) — white-favored layout, dark navbar still looks correct

### Global
- [ ] Navbar — dark blur, no glow under CTA button, links visible
- [ ] Footer — 4-column layout, brand name, Calendly CTA
- [ ] Mobile nav — offcanvas drawer is dark, links visible

### Common Issues to Watch For
| Symptom | Likely Cause | Fix |
|---|---|---|
| Navbar looks lighter/greyer on a page | A section or body has a light background bleeding through the blur | Check that `body` stays `#071222`; give sections explicit white backgrounds instead |
| Content hidden under navbar | `#wrapwrap` missing `padding-top: 68px` | Confirm global CSS view is active on production |
| Blog cards show white text on light bg | `card-body` background override missing | Check `article.o_wblog_post .card-body { background: transparent !important }` |
| CSS view not applying | View is inactive, or wrong `inherit_id` | Check `ir.ui.view` record; set `active = True` |
| Meta not showing in browser tab | Browser cache | Hard refresh (`Cmd+Shift+R`) or check in incognito |

---

## Rollback

The migration script automatically backs up the current production state before making any changes. The rollback command is printed at the end of every successful migration run.

### How the backup works

Before the first write, the script snapshots:
- The arch of every view it will update (footer, CSS views, page arches)
- The current meta title and description for every page in `META_UPDATES`
- Which CSS views did not exist yet (so rollback knows to delete them rather than restore them)

Backups are saved to `.tmp/prod_backup_{timestamp}/` and contain a `manifest.json` plus individual `.arch` files.

### Running a rollback

The rollback command is printed at the end of every migration run:
```
To rollback: python3 tools/migrate_to_production.py --rollback .tmp/prod_backup_20260307_153000
```

Or find the latest backup and run:
```bash
ls -dt .tmp/prod_backup_* | head -1   # find most recent backup dir
python3 tools/migrate_to_production.py --rollback .tmp/prod_backup_20260307_153000
```

### What rollback does per item

| Item | If migration updated it | If migration created it (didn't exist before) |
|---|---|---|
| Footer | Restores original arch | N/A — footer always exists |
| CSS views (global, blog, ICP) | Restores original arch | **Deletes** the view |
| Page arches (/, /about) | Restores original arch | N/A — pages always exist |
| Meta fields | Restores previous title + description (blank if they were empty) | Same |

### What rollback does NOT cover

- Pages created fresh during migration (not in this current script, but relevant if extended)
- Any manual edits made via the Odoo website editor after the migration ran
- Changes made outside the migration script (e.g., manual edits in Odoo backend)

### If the backup is missing

If `.tmp/prod_backup_*/` was deleted or the migration was interrupted before backup completed, restore manually:

**Page arches** — fetch current live arch and compare:
```bash
python3 tools/get_page.py --url /
python3 tools/get_page.py --url /about
```

**CSS views** — go to Odoo backend → Settings → Technical → User Interface → Views, search your project name, and delete or edit as needed.

**Meta** — Odoo backend → Website → Pages, open each page's properties and clear/restore the meta fields manually.
