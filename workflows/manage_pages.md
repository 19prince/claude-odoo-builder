# Manage Pages Workflow

## Objective
Reference SOP for all read, update, publish, and inspection operations on existing Odoo website pages. Use this when the user wants to see what's on their site, edit existing content, or change page visibility.

---

## Operations

### List All Pages
```bash
python3 tools/list_pages.py
```
Output: table with ID, URL, name, view_id, published status, homepage flag.
Raw JSON saved to `.tmp/pages_list.json`.

Filter to published pages only:
```bash
python3 tools/list_pages.py --published-only
```

Filter by specific URL:
```bash
python3 tools/list_pages.py --url /about
```

---

### Fetch a Page's HTML Content
```bash
python3 tools/get_page.py --url /about
# or by ID:
python3 tools/get_page.py --id 42
```

Output: arch HTML printed to terminal + saved to `.tmp/page_about.html`.

**Always run `get_page.py` before editing a page** — it creates a backup automatically.

---

### Update a Page's Content
After editing `.tmp/page_about.html` (or a fresh draft):
```bash
python3 tools/push_page.py --update --url /about --file .tmp/page_about.html
```

A backup of the pre-update arch is saved to `.tmp/backup_about.html`.

Full update flow: `get_page.py` → edit file → `validate_html.py` → `push_page.py --update`

---

### Publish a Page
```bash
python3 tools/push_page.py --publish --url /about
```

### Unpublish a Page
```bash
python3 tools/push_page.py --unpublish --url /about
```

---

### Delete a Page
Deletion is intentionally not automated — it's irreversible. Use the Odoo backend:
1. Odoo backend → Website → Pages
2. Select the page → Action → Delete

Or (advanced): Website module → Settings → Pages menu.

---

## Data Model Reference

### `website.page` — page records
| Field | Type | Notes |
|---|---|---|
| `id` | int | Record ID |
| `name` | str | Human-readable title |
| `url` | str | URL path, e.g. `/about` |
| `view_id` | many2one | Linked `ir.ui.view` ID |
| `website_published` | bool | `True` = publicly visible |
| `is_homepage` | bool | `True` = set as homepage |
| `active` | bool | `False` = soft-deleted |
| `website_id` | many2one | Multi-website: which website |

### `ir.ui.view` — the arch (HTML/QWeb content)
| Field | Type | Notes |
|---|---|---|
| `id` | int | Record ID |
| `name` | str | Technical name |
| `arch` | str | Full XML/HTML template content |
| `type` | str | Always `qweb` for website views |
| `key` | str | Dotted key, e.g. `website.page_about` |
| `inherit_id` | many2one | Parent view (for inherited views) |

The arch on `ir.ui.view` is what push_page.py writes to. The `website.page` record
is a thin wrapper that adds URL routing and publish/unpublish control.

---

## Common Search Domains

```python
# All published pages
[("website_published", "=", True)]

# All active (non-deleted) pages
[("active", "=", True)]

# Find by URL
[("url", "=", "/about")]

# Homepage
[("is_homepage", "=", True)]

# Multi-website: pages for website ID 2
[("website_id", "=", 2)]

# Pages containing a keyword in the name
[("name", "ilike", "contact")]
```

These domains can be passed directly to `odoo_client.search_read()` if writing custom scripts.

---

## Troubleshooting

| Problem | Fix |
|---|---|
| `list_pages.py` returns 0 results | Check user has "Website" access rights in Odoo Settings |
| Arch appears truncated | Use `get_page.py --id` to fetch by record ID (avoids URL routing issues) |
| Page exists in Odoo but not in list | Check `active=False` — page may be soft-deleted; use domain `[("active","in",[True,False])]` |
| Multi-website: seeing wrong site's pages | Confirm which `website_id` is active; add `--website-id` filter to search |
| Page updates don't appear in browser | Clear Odoo's asset cache: Settings → Technical → Clear Server Assets, or add `?nocache=1` to URL |

---

## Tips for Working Efficiently

1. **Always fetch before editing** — `get_page.py` creates the backup that enables rollback
2. **Keep drafts versioned** — rename `.tmp/draft_about_v2.html` etc. to track iterations
3. **Batch inspection** — `.tmp/pages_list.json` can be parsed to build a site map
4. **Compare versions** — `diff .tmp/backup_about.html .tmp/draft_about.html` to review changes before pushing
5. **Test unpublished** — push first, open `/web/preview?url=/about` in Odoo to preview before publishing
