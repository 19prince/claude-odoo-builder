# Push to Odoo Workflow

## Objective
Authenticate with Odoo and push a validated HTML draft to a website page — either creating a new page or updating an existing one. Includes rollback instructions.

## Required Inputs
- Source HTML file (e.g., `.tmp/draft_about.html`)
- Target page URL (e.g., `/about`)
- Page name — required for `--create` (e.g., "About Us")
- `.env` populated with: `ODOO_URL`, `ODOO_DB`, `ODOO_USER`, `ODOO_PASSWORD`

---

## Pre-Flight Checks

### 1. Verify credentials
Open `.env` and confirm all four Odoo keys are set. If any are blank:
- Stop here and ask the user to provide them
- Do NOT attempt to push with placeholder values

### 2. Validate the HTML
```bash
python3 tools/validate_html.py --input .tmp/draft_{slug}.html
```
- Do NOT proceed if validation exits with code 1 (errors found)
- Warnings are acceptable but review them before pushing

### 3. Confirm with user
Before touching the live site, confirm:
> "Ready to push '{Page Name}' to `{ODOO_URL}{url}`. This will modify the live site. Proceed?"

If the user wants to test first: push as unpublished (default), then use `--publish` only after visual review.

---

## Step 1: Check if Page Already Exists

```bash
python3 tools/list_pages.py --url {url}
```

- **No results** → use CREATE path (Step 2)
- **Results found** → use UPDATE path (Step 3)

---

## Step 2: CREATE a New Page

```bash
python3 tools/push_page.py --create \
  --name "About Us" \
  --url /about \
  --file .tmp/draft_about.html
```

What this does:
1. Reads the HTML file
2. Wraps it in the QWeb `<t t-name=...>` template automatically
3. Creates an `ir.ui.view` record (the arch)
4. Creates a `website.page` record linked to the view
5. Page is created as **unpublished** by default

Verify creation:
```bash
python3 tools/list_pages.py --url /about
```

---

## Step 3: UPDATE an Existing Page

```bash
python3 tools/push_page.py --update \
  --url /about \
  --file .tmp/draft_about.html
```

What this does:
1. Fetches the current page's `view_id`
2. **Saves a backup** of the current arch to `.tmp/backup_about.html`
3. Writes the new arch to `ir.ui.view`

Note: `--update` does not change published/unpublished status.

---

## Step 4: Publish the Page (when ready)

```bash
python3 tools/push_page.py --publish --url /about
```

To unpublish:
```bash
python3 tools/push_page.py --unpublish --url /about
```

---

## Step 5: Verify

Ask the user to:
1. Open `{ODOO_URL}/about` in a browser to verify visual appearance
2. Open the Odoo Website Editor (Edit button) to confirm all regions are editable
3. Test on mobile view (Odoo editor has a responsive preview toggle)

If something looks wrong:
```bash
python3 tools/get_page.py --url /about
```
This fetches the live arch back. Compare to the file you pushed.

---

## Rollback

If a push caused issues, restore the pre-push backup:
```bash
python3 tools/push_page.py --update \
  --url /about \
  --file .tmp/backup_about.html
```

Backups are created automatically by `--update`. For `--create`, there is no prior state to roll back to — delete the page from the Odoo backend if needed.

---

## Error Reference

| Error message | Cause | Fix |
|---|---|---|
| `Authentication failed` | Wrong credentials | Check `ODOO_USER` and `ODOO_PASSWORD` in `.env` |
| `Access Denied` | User lacks Website Admin rights | Grant "Website" access in Odoo Settings > Users |
| `Record not found` / no page at URL | URL may have changed | Run `list_pages.py` to find the current URL |
| `Odoo error: Invalid arch` | Malformed QWeb/HTML | Run `validate_html.py`, check for unclosed `<t>` tags |
| `HTTP error: Connection refused` | Wrong `ODOO_URL` | Verify URL in `.env`; confirm server is running |
| `A page already exists at {url}` | Tried `--create` on existing URL | Switch to `--update` |

---

## Odoo RPC Reference (for debugging)

All calls go to: `POST {ODOO_URL}/web/dataset/call_kw`

Authenticate:
```json
{"model": "res.users", "method": "authenticate", "args": ["db", "user", "pass", {}]}
```

Read pages:
```json
{"model": "website.page", "method": "search_read", "args": [[["url","=","/about"]]], "kwargs": {"fields": ["id","name","view_id"]}}
```

Write arch:
```json
{"model": "ir.ui.view", "method": "write", "args": [[view_id], {"arch": "<t t-name=...>...</t>"}]}
```
