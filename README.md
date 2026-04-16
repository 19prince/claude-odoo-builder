# Claude Odoo Builder

Turn [Claude Code](https://docs.anthropic.com/en/docs/claude-code/overview) into an Odoo website builder. One command scaffolds a complete project with tools, workflows, and configuration for designing, building, and deploying pages on your Odoo website.

# Disclaimer
By downloading and deploying these files, you take full responsibility. Neither [19 Prince](https://www.19prince.com/) nor Darren are responsible for productivity gains, productivity losses, injury due to falling down rabbit holes, lost sleep, or the annoying conversations you'll feel the need to have about Claude Code.

Seriously, I tried to provide you with some useful tools. I genuinely hope you like them. That said, read the files and be safe out there. You are taking full responsibility for any and all outcomes.

---

## What's Included

### Skills

| Skill | Trigger | What it does |
|-------|---------|-------------|
| **new-odoo-project** | `/new-odoo-project` | Scaffolds a full Odoo website builder project — tools, workflows, `.env`, and `CLAUDE.md` |
| **odoo-theme-fix** | Share a screenshot + ask for fixes | Reviews a page screenshot, writes targeted CSS overrides, and pushes them via RPC |

### Tools (Python scripts)

| Tool | Purpose |
|------|---------|
| `odoo_client.py` | Shared Odoo JSON-RPC client used by all other tools |
| `get_page.py` | Fetch any page's HTML with automatic backup |
| `list_pages.py` | List all website pages with publish status |
| `push_page.py` | Create or update pages with QWeb wrapping |
| `validate_html.py` | Pre-push HTML validator for Odoo compatibility |
| `scaffold_snippet.py` | Generate custom snippet module skeletons |
| `migrate_to_production.py` | Migrate staging changes to production with backup and rollback |

### Workflows (Markdown SOPs)

| Workflow | Purpose |
|----------|---------|
| `design_page.md` | Step-by-step guide for designing new pages |
| `design_system.md` | Bootstrap/Odoo reference with 13 paste-ready section templates |
| `push_to_odoo.md` | How to push content to Odoo safely |
| `css_theming.md` | CSS injection via `custom_code_head` |
| `create_snippet.md` | How to build and deploy custom snippet modules |
| `manage_pages.md` | Page operations reference (list, fetch, update, delete) |
| `migrate_staging_to_prod.md` | Full migration guide with dry-run and rollback |

---

## Prerequisites

- [Claude Code](https://docs.anthropic.com/en/docs/claude-code/overview) installed
- Python 3.8+
- An Odoo instance with admin access (URL, database name, login email)

---

## Installation

1. Clone this repo:

```bash
git clone https://github.com/19prince/claude-odoo-builder.git
```

2. Copy the skills into your Claude Code skills directory:

```bash
cp -r claude-odoo-builder/skills/* ~/.claude/skills/
```

3. Install Python dependencies:

```bash
pip install requests python-dotenv
```

---

## Quick Start

Open Claude Code in your terminal and type:

```
/new-odoo-project
```

Claude will ask you for:

1. **Project directory** — where the project should live
2. **Client/project name** — a short name for your project
3. **Odoo URL** — your Odoo instance URL
4. **Database name** — your Odoo database name
5. **Login email** — the email you use to log into Odoo
6. **Staging or production?** — whether you have a separate staging server

Claude creates the project structure and a `.env` file with your credentials template. You fill in the password yourself — Claude never sees it.

---

## After Setup

### Add your password

Open the `.env` file in your project and fill in `ODOO_PASSWORD=`:

```bash
nano ~/projects/my-website/.env
```

### Verify the connection

Claude automatically tests the connection. If it works, you'll see all your website pages listed with their publish status.

### Check the website editor

Log into your Odoo backend, open the website editor, and verify:
- Snippet block thumbnails load without warning icons
- You can drag blocks onto the page
- Text and image toolbars appear when clicking elements

If blocks show orange warning icons, tell Claude — there's a quick fix (installing `theme_clean`).

---

## What You Can Do

### Design and build pages
Tell Claude what page you want. It plans the layout, writes Odoo-compatible HTML using paste-ready templates, validates it, and pushes it to your website.

### Style with CSS
Claude injects custom CSS through Odoo's `custom_code_head` — no theme module needed. Describe what you want changed and it writes scoped CSS.

### Manage pages
List all pages, fetch HTML for editing, publish or unpublish, create new pages from scratch.

### Fix visual issues from screenshots
Share a screenshot and Claude identifies broken elements, writes targeted CSS fixes, and pushes them — all without touching page content.

### Migrate staging to production
Build on staging, then migrate to production with automatic backup and one-command rollback.

---

## Project Structure

After setup, your project folder looks like this:

```
my-website/
  .env            # Your Odoo credentials (never shared)
  CLAUDE.md       # Instructions Claude reads every session
  .tmp/           # Temporary working files
  tools/          # Python scripts that talk to Odoo
  workflows/      # Step-by-step guides Claude follows
```

---

## Tips

- **Always dry-run before migrating** — the migration tool has a `--dry-run` flag
- **Claude reads workflows automatically** — ask it to design a page and it reads `design_page.md` first
- **Everything is backed up** — before any destructive operation, tools save a backup to `.tmp/`
- **Passwords stay local** — only in your `.env` file, which is never committed

---

## License

MIT — see [LICENSE](LICENSE).
