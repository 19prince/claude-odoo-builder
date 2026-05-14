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

```
.tmp/       # Temporary files — regenerated as needed
tools/      # Python scripts
workflows/  # Markdown SOPs
.env        # Credentials — NEVER commit this
```

## Project: 19prince

- **Server:** https://19prince-staging-30854879.dev.odoo.com
- **DB:** 19prince-staging-30854879
- **Brand colors:** TBD
- **Brand fonts:** TBD
- **Design direction:** TBD
- **Logo:** TBD

## Key Workflows

- `workflows/design_page.md` — designing and building pages
- `workflows/push_to_odoo.md` — pushing content to Odoo as a **website page** (`website.page`)
- `workflows/create_blog_post.md` — creating and publishing **blog posts** (`blog.post`) — use this, NOT push_to_odoo, for blog content
- `workflows/css_theming.md` — CSS injection pattern
- `workflows/design_survey.md` — designing and creating Odoo surveys
- `workflows/migrate_staging_to_prod.md` — staging → production migration

## Rules

- Always read a workflow before starting a task that matches it
- Never store secrets anywhere except `.env`
- Validate HTML before pushing: `python3 tools/validate_html.py --input .tmp/draft.html`
- Always dry-run before migrating to production
