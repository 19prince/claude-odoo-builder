# Git Cleanup — 19prince repo (guidance note)

Written 2026-06-06. The repo is barely tracked: only files committed this session are on branch
`docs/crm-state-changes-design`. Almost everything in `git status` is untracked — a mix of real
source and junk, with NO `.gitignore`.

## Why this matters
- Your core tools (`tools/crm_review_server.py`, `push_crm_updates.py`, `odoo_client.py`, etc.) are
  NOT version-controlled. This session's server edits weren't protected until manually committed.
- No history = no diffs, no safe revert, easy accidental loss.
- Without a `.gitignore`, the natural fix (`git add -A`) would also commit junk and possibly secrets.

## ⚠️ Do this FIRST — secrets check
Before committing anything broadly, confirm no credentials get tracked:
- Check how `tools/odoo_client.py` gets its Odoo URL/login/password (env var? hardcoded? a config file?).
- If there's a `.env`, API keys, or a creds file, it MUST go in `.gitignore` and never be committed.
- Scan: `grep -rinE "password|api[_-]?key|secret|token" tools/ *.py 2>/dev/null`

## Decisions I need from you (the "guidance" part)
1. **Track vs ignore.** Proposed:
   - TRACK: `tools/`, `workflows/`, `docs/` (source + docs).
   - IGNORE: `.DS_Store`, `*.mp4`, large binaries/images, data CSVs (`add-emails.csv` etc.),
     `.python-version`?, `.claude/`, `docs/superpowers/`, `design_handoff_*` / `editor_tldr_style/`
     / `19 Prince Design System/` (are these source or scratch?).
   → Which of those folders are real source you want tracked vs local scratch?
2. **Media policy.** Track small committed assets, or keep all media out of git (recommend out)?
3. **Branch.** Do cleanup on a new branch (e.g., `chore/git-baseline`), review together, then merge to main.

## Recommended `.gitignore` (starting point)
```
.DS_Store
.python-version
.claude/
__pycache__/
*.pyc
# secrets — adjust to actual filenames
.env
*.secret
# bulk media + data exports
*.mp4
*.png
*.jpg
*.jpeg
*.webp
*.csv
```

## Steps (we do this together so you can intervene at each gate)
1. Secrets check above.
2. Create branch `chore/git-baseline`.
3. Add `.gitignore`.
4. Explicitly `git add` only the agreed source paths (not `-A`): `git add tools workflows docs .gitignore`.
5. Review `git status` together — confirm nothing unexpected is staged.
6. Commit: "Establish tracked baseline for tools/workflows/docs + .gitignore".
7. Merge `docs/crm-state-changes-design` and this baseline into `main` once you're happy.

## How to start next session
Say "git hygiene" (menu item C in `Vault DEO/19Prince-Ops/2026-06-06-session-handoff.md`) and I'll
walk you through steps 1–7, pausing for your decisions on #1–#3 above.
```
