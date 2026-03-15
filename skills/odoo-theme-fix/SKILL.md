# Skill: odoo-theme-fix

TRIGGER: User shares a screenshot of an Odoo page and asks for visual fixes, theming improvements, or readability changes.

## What this skill does

Reviews an Odoo page screenshot against the blueprint dark theme, identifies broken or mismatched elements, writes targeted CSS overrides, and pushes them to `website.custom_code_head` via RPC — without touching any page arch.

---

## Instructions

When invoked:

1. **Read the screenshot** — identify every element that is wrong:
   - White or light backgrounds that should be dark (`#071222`)
   - Dark text on dark backgrounds (contrast failure)
   - Default Odoo colors breaking the blueprint palette
   - Unstyled form inputs, search bars, cards, pagination, badges

2. **Read `workflows/css_theming.md`** — check the known selector map before writing anything new. Reuse confirmed selectors. Add new ones only when needed.

3. **Read the current `custom_code_head`**:
   ```python
   sites = c.search_read("website", [], ["id", "custom_code_head"])
   ```

4. **Write a targeted `<style>` block** following these rules:
   - Use the blueprint palette: `#071222` bg, `#0a1c33` card bg, `#3b8eea` / `#5da8ff` / `#7ec8ff` blues, `#ffffff` headings, `rgba(255,255,255,.82)` body, `rgba(255,255,255,.6)` muted
   - Scope every selector to the page's body class (e.g. `.o_wblog_index`, `.o_wblog_post_page`) to avoid leaking styles globally
   - Use `!important` on color and background overrides — Odoo's specificity is high
   - Wrap the block in `/* == [section name] start == */` and `/* == [section name] end == */` CSS comments so it can be cleanly replaced later
   - Strip the previous block for that section before appending the new one (use `re.sub` with `DOTALL`)

5. **Push via RPC**:
   ```python
   c.write("website", [site_id], {"custom_code_head": new_head})
   ```

6. **Confirm** what changed and ask for a follow-up screenshot to verify.

---

## Blueprint Palette Reference

| Role | Value |
|---|---|
| Page background | `#071222` |
| Card / panel background | `rgba(10,28,51,.85)` |
| Elevated surface | `#0a1c33` |
| Primary blue | `#3b8eea` |
| Bright blue (links, accents) | `#5da8ff` |
| Light blue (muted accents) | `#7ec8ff` |
| Heading text | `#ffffff` |
| Body text | `rgba(255,255,255,.82)` |
| Muted text | `rgba(255,255,255,.55)` |
| Subtle text | `rgba(255,255,255,.4)` |
| Card border | `rgba(59,142,234,.22)` |
| Divider | `rgba(59,142,234,.18)` |
| Blueprint grid line | `rgba(59,142,234,.07)` |
| Success green | `#4ade80` |
| Error red | `#f87171` |
| Warning amber | `#fbbf24` |

---

## Do Not

- Do not modify `ir.ui.view` arch or `website.page` records — CSS only
- Do not use broad unscoped selectors like `h1 { color: white }` — always scope to a page class
- Do not push without running a `re.sub` cleanup of any previous block for that section
- Do not add visible text markers in the HTML — markers must be CSS comments inside `<style>` tags
