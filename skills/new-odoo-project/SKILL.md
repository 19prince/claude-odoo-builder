# Skill: new-odoo-project

TRIGGER: User invokes `/new-odoo-project` to scaffold a new Odoo website builder project.

## Objective
Scaffold a new Odoo website builder project directory, copy all bundled tools and workflows from the skill's `templates/` directory, create a configured `.env` template, and orient the user for their first session.

---

## Prerequisites

Before running this skill, ensure the following are in place:

1. **Python 3.8+** installed and available as `python3`
2. **Python packages** — install from the bundled requirements file:
   ```bash
   pip install -r {skill_dir}/templates/requirements.txt
   ```
   This installs `requests` and `python-dotenv`, the only third-party dependencies.
3. **An Odoo instance** with admin or API access (URL, database name, and login email)
4. **Claude Code** — this skill is designed for Claude Code's skill system

---

## Step 1 — Gather technical information (ask all at once)

Ask the user for the following in a single message. Do not proceed until you have answers:

1. **Project directory path** — where should the project live? (e.g. `~/projects/client-acme-website`)
2. **Client / project name** — used for folder naming and memory
3. **Odoo URL** — e.g. `https://mysite.odoo.com`
4. **Odoo DB name** — e.g. `mysite-main-12345`
5. **Odoo login email**
6. **Is this a production-only server, or is there a separate staging instance?**
   - If staging + production: collect both URLs and DB names (but NOT passwords)
   - If production only: note that changes go live immediately — extra caution required

Do NOT ask for any passwords. Tell the user: "I'll leave the password fields blank in `.env` — fill those in yourself before running any tools."

Do NOT ask about brand, fonts, or design yet — those come after the project is set up.

---

## Step 2 — Create the project directory

```bash
mkdir -p {project_dir}/tools
mkdir -p {project_dir}/workflows
mkdir -p {project_dir}/.tmp
```

---

## Step 3 — Copy tools from skill templates

Copy all `.py` files from the skill's bundled templates. The skill's base directory is provided when invoked — use it to locate `templates/tools/`:

```bash
cp {skill_dir}/templates/tools/*.py {project_dir}/tools/
```

The `migrate_to_production.py` template ships pre-cleaned with empty `META_UPDATES`, `CSS_VIEW_KEYS`, and `PAGE_URLS` lists, and a clean `main()` with commented examples. No post-copy cleanup is needed.

---

## Step 4 — Copy workflows from skill templates

```bash
cp {skill_dir}/templates/workflows/*.md {project_dir}/workflows/
```

Workflows are generic and apply to any Odoo project without modification.

---

## Step 4b — Create `.gitignore`

Write `.gitignore` to the project root to prevent committing secrets and temporary files:

```
# Credentials
.env

# Temporary files
.tmp/

# Python
__pycache__/
*.pyc
*.pyo

# OS files
.DS_Store
Thumbs.db

# IDE
.vscode/
.idea/
```

---

## Step 5 — Create `.env`

Write `.env` to the project root. **Leave all password fields blank.**

For a staging + production setup:
```
# Staging
ODOO_URL={staging_url}
ODOO_DB={staging_db}
ODOO_USER={login_email}
ODOO_PASSWORD=

# Production (fill in when ready to migrate)
# PROD_ODOO_URL={prod_url}
# PROD_ODOO_DB={prod_db}
# PROD_ODOO_USER=
# PROD_ODOO_PASSWORD=
```

For a production-only setup:
```
# Production (working directly on production — no staging)
ODOO_URL={odoo_url}
ODOO_DB={odoo_db}
ODOO_USER={login_email}
ODOO_PASSWORD=
```

---

## Step 6 — Create `CLAUDE.md`

Write `CLAUDE.md` to the project root using this template:

```markdown
# Agent Instructions

You're working inside the **WAT framework** (Workflows, Agents, Tools).

## The WAT Architecture

**Layer 1: Workflows** — Markdown SOPs in `workflows/`
**Layer 2: Agents** — Your role: read workflows, run tools, handle failures
**Layer 3: Tools** — Python scripts in `tools/` for deterministic execution

## How to Operate

1. Look for existing tools before building new ones
2. Learn and adapt when things fail — update workflows with findings
3. Keep workflows current as the project evolves

## File Structure

\`\`\`
.tmp/       # Temporary files — regenerated as needed
tools/      # Python scripts
workflows/  # Markdown SOPs
.env        # Credentials — NEVER commit this
\`\`\`

## Project: {client_name}

- **Server:** {odoo_url}
- **DB:** {odoo_db}
- **Brand colors:** TBD
- **Brand fonts:** TBD
- **Design direction:** TBD
- **Logo:** TBD

> ⚠️ [Production-only note if applicable: This project works directly on production. There is no separate staging server. Always use `--dry-run` before any migration. Be extra careful — changes go live immediately.]

## Key Workflows

- `workflows/design_page.md` — designing and building pages
- `workflows/push_to_odoo.md` — pushing content to Odoo
- `workflows/css_theming.md` — CSS injection pattern
- `workflows/migrate_staging_to_prod.md` — staging → production migration

## Rules

- Always read a workflow before starting a task that matches it
- Never store secrets anywhere except `.env`
- Validate HTML before pushing: `python3 tools/validate_html.py --input .tmp/draft.html`
- Always dry-run before migrating to production
```

---

## Step 7 — Verify setup

Run a connection test:

```bash
cd {project_dir} && python3 -c "
import sys; sys.path.insert(0, 'tools')
from odoo_client import OdooClient
c = OdooClient()
uid = c.authenticate()
print('Connected — uid:', uid)
pages = c.search_read('website.page', [('active','=',True)], ['url','name','is_published'])
print(f'{len(pages)} pages found:')
for p in sorted(pages, key=lambda x: x['url']):
    pub = 'published' if p['is_published'] else 'draft'
    print(f'  {p[\"url\"]:<35} {pub}')
"
```

**If authentication error:** remind the user to fill in `ODOO_PASSWORD` in `.env`.

**If connection error:** ask the user to double-check `ODOO_URL` and `ODOO_DB`.

---

## Step 8 — Verify the WYSIWYG editor and snippet blocks

This step must be done by the user in a browser. Instruct them to:

1. Log into the Odoo backend and open the website editor on any page (click **Edit** in the top bar)
2. Look at the right-hand **Blocks** panel — confirm snippet thumbnails load with no orange **!** warning icons
3. Drag any block (e.g. a Text block) onto the page — confirm it drops and renders without errors
4. Click an existing text element — confirm the formatting toolbar appears
5. Click an existing image — confirm the image toolbar appears

If snippet blocks show orange **!** icons (all or most of them):

**Root cause:** No theme is linked to the website (`theme_id = False`). This causes Odoo's snippet rendering to fail.

**Fix — install and link `theme_clean`:**

```bash
python3 - <<'EOF'
import sys
sys.path.insert(0, 'tools')
from odoo_client import OdooClient

c = OdooClient()
c.authenticate()

# Find theme_clean module
modules = c.search_read("ir.module.module", [["name", "=", "theme_clean"]], ["id", "name", "state"])
print("theme_clean:", modules)

# If state is 'uninstalled', install it
if modules and modules[0]["state"] == "uninstalled":
    module_id = modules[0]["id"]
    c._execute_kw("ir.module.module", "button_immediate_install", [[module_id]], {})
    print("Installed theme_clean")

# Link theme to website
sites = c.search_read("website", [], ["id", "name", "theme_id"])
print("Sites:", sites)

theme_module = c.search_read("ir.module.module", [["name", "=", "theme_clean"]], ["id"])
theme_id = theme_module[0]["id"]
c.write("website", [sites[0]["id"]], {"theme_id": theme_id})
print(f"Linked theme_clean (id={theme_id}) to website {sites[0]['id']}")
EOF
```

After running, ask the user to hard-refresh the editor page (`Cmd+Shift+R`) and confirm the orange icons are gone.

**Important:** After installing `theme_clean`, re-push any existing `custom_code_head` CSS — the theme installation may reset the field.

If the editor toolbar appears but **JS errors** occur in the console, check `custom_code_head` for any `<script>` tags — JS in `custom_code_head` breaks the editor widget panel. Remove all `<script>` blocks and use CSS-only approaches instead.

---

## Step 9 — Gather branding information

Now that the project is set up and connected, ask the user for branding details in a single message:

1. **Brand colors** — primary, secondary, background (or "TBD")
2. **Brand fonts** — or "TBD"
3. **Design direction** — e.g. dark theme, light theme, minimal, bold (or "TBD")
4. **Logo** — do they have a logo file, or is it text-only? (or "TBD")

Once answered (even if all "TBD"), update `CLAUDE.md` with the values:
- Replace `{brand_colors}`, `{brand_fonts}`, `{design_direction}` placeholders with the actual answers

---

## Step 10 — Save to memory

Create a memory file for this project. Determine the memory path from the project directory path by converting it to the Claude project slug format (replace `/` with `-`, strip leading `-`).

Memory file location: `~/.claude/projects/{slugified_project_dir}/memory/MEMORY.md`

Include:
- Client name and project directory
- Odoo URL and DB
- Brand colors, fonts, and design direction (even if TBD)
- Logo notes if provided
- Production URL and DB if provided
- Note if production-only (no staging)

---

## Step 11 — Output summary

Print a clean summary:

```
Project scaffolded: {project_dir}

  tools/          — Python scripts (from skill templates)
  workflows/      — Markdown SOPs (from skill templates)
  .env            — fill in ODOO_PASSWORD before running tools
  CLAUDE.md       — project instructions written

Next steps:
  1. Fill in ODOO_PASSWORD in .env
  2. Open a new Claude Code session pointed at {project_dir}
  3. Verify connection: python3 tools/list_pages.py
```

---

## Notes

- Never ask for passwords — always leave password fields blank for the user to fill in
- Brand/font/design questions come in Step 9, after the project is set up and connected — never ask them upfront
- If the user says "TBD" for any brand field, write "TBD" in CLAUDE.md — it can be updated later
- The `migrate_to_production.py` `META_UPDATES` list starts empty — it gets populated as meta descriptions are written during the project
- The `.tmp/` directory starts empty — that's correct
- For production-only projects, add the `⚠️` warning to CLAUDE.md and remind the user throughout the session that changes are live immediately

---

## Appendix — Complete Odoo Theming Checklist

Use this as a tracking checklist at the start of every project. Every surface below needs to be reviewed and styled (or explicitly accepted as default). Check each off as CSS is pushed to `custom_code_head`.

### Pages (full-page layouts)

| Surface | URL | Body class / selector | Notes |
|---|---|---|---|
| Homepage | `/` | — | Custom page arch |
| Shop listing | `/shop` | `.oe_website_sale` | Product grid, filters, pagination |
| Shop category | `/shop?category=N` | `.oe_website_sale` | Same as shop listing |
| Product detail | `/shop/product/…` | `#product_detail` | PDP — name, price, add-to-cart, tabs |
| Shopping cart | `/shop/cart` | `.o_cart_summary`, `#cart_total` | Line items, totals, checkout CTA |
| Checkout | `/shop/checkout` | `.o_website_sale_checkout` | Address form, payment, confirm button |
| Order confirmation | `/shop/confirmation` | `.o_website_sale_confirmation` | Thank-you message, order summary |
| Contact form | `/contactus` | `.o_wcontact` | Form fields, submit button |
| Contact thank-you | `/contactus-thank-you` | `.o_wcontact` | Post-submit confirmation message |
| 404 / error | `/web/404` | `.o_website_error` | Odoo default error page |
| Blog listing | `/blog` | `.o_wblog_index` | Post cards, sidebar, pagination |
| Blog post | `/blog/…/…` | `.o_wblog_post_page` | Post header, content, author, related posts |
| Login | `/web/login` | `.o_login_form` | Separate from website layout — needs scoped CSS |
| Signup / Register | `/web/signup` | `.o_signup_form` | Same caveat as login |
| Customer portal home | `/my/home` | `.o_portal_wrap` | Portal layout is separate from website layout |
| My Orders | `/my/orders` | `.o_portal_wrap` | Order list |
| Order detail | `/my/orders/N` | `.o_portal_wrap` | Line items, status, download PDF |
| My Account | `/my/account` | `.o_portal_wrap` | Profile / address edit form |
| Wishlist | `/shop/wishlist` | `.o_wsale_wishlist` | Only if Wishlist module is installed |

### UI Elements (overlays, modals, popups, widgets)

| Element | Selector | Notes |
|---|---|---|
| Cookie consent banner | `.o_cookies_bar`, `.o_cookies_popup` | Appears on first visit |
| "Added to cart" toast | `.o_notification_manager`, `.o_cart_notification` | Triggered on add-to-cart |
| Product quick-view modal | `.o_wsale_product_modal` | Shop listing — if quick-view is enabled |
| Search overlay / autocomplete | `.o_searchbar_autocomplete`, `.o_search_modal` | Global site search |
| Newsletter popup | `.o_newsletter_popup` | If Newsletter popup snippet is placed |
| Mobile nav drawer | `#o_offcanvas_menu` | Hamburger menu on mobile |
| Live chat widget | `.o_livechat_button`, `#im_livechat` | If Livechat module is installed |
| Wishlist sidebar | `.o_wsale_wishlist_sidebar` | If Wishlist module is installed |
| My Account dropdown | `.o_user_additional_menu` | Top-right user menu when logged in |

### How to use this checklist

1. At the start of the project, paste this checklist into `.tmp/theming_checklist.md`
2. Mark each row `[ ]` (not done), `[x]` (styled), or `[—]` (skipped / not applicable)
3. After pushing each CSS block, update the checklist
4. Do not mark a project complete until all applicable rows are checked
