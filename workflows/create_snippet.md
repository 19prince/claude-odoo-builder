# Create Custom Snippet Workflow

## Objective
Package a reusable HTML/CSS/JS design element as a proper Odoo module so it appears in the Website Editor's snippet panel and can be drag-dropped onto any page.

## When to Use This vs. Direct Push

| Situation | Use |
|---|---|
| One-off page content | Direct push via `push_to_odoo.md` |
| Element reused on 2+ pages | This workflow |
| Needs scoped SCSS (won't leak to other pages) | This workflow |
| Needs custom JS (animations, counters, tabs) | This workflow |
| User has access to deploy Odoo modules | This workflow |
| Odoo.com SaaS (no custom modules allowed) | Direct push only |

---

## Required Inputs
- **Technical name** — snake_case, no spaces (e.g., `hero_split_screen`)
- **Display name** — shown in editor panel (e.g., "Hero Split Screen")
- **HTML template** — the section content (or start from scaffold default)
- **Custom SCSS** (optional)
- **Custom JS** (optional)
- **Odoo version** — affects asset bundle names

---

## Step 1: Scaffold the Module

```bash
python3 tools/scaffold_snippet.py \
  --name hero_split_screen \
  --label "Hero Split Screen" \
  --odoo-version 17
```

This creates a complete module skeleton at:
```
.tmp/snippets/hero_split_screen/
├── __manifest__.py
├── __init__.py
├── views/
│   ├── snippets.xml     ← snippet HTML template + editor registration
│   └── assets.xml       ← asset bundle reference (fallback for old Odoo)
└── static/src/
    ├── scss/snippet.scss
    └── js/snippet.js
```

---

## Step 2: Customize the Snippet Template

Open `views/snippets.xml`.

**Key parts of the template:**
```xml
<template id="s_hero_split_screen" name="Hero Split Screen">
  <section class="s_hero_split_screen o_colored_level py-5"
           data-snippet="hero_split_screen.s_hero_split_screen"
           data-name="Hero Split Screen">
    <!-- your HTML goes here -->
  </section>
</template>
```

Rules:
- Root element MUST be `<section>`
- `data-snippet` must match `{module_name}.{template_id}`
- `data-name` is the tooltip shown in the editor
- Never use `id=""` attributes — multiple snippet instances can exist on one page
- Use `class="o_editable"` on every text container the user should be able to edit
- Use `class="img-fluid"` on every `<img>`
- CSS class on the section must be `s_{technical_name}` — this is the snippet's identity

**Snippet option widgets** (add inside the `snippets_registration` XPath to expose editor controls):
```xml
<div data-selector=".s_hero_split_screen">
  <!-- Toggle class modifier -->
  <we-checkbox string="Dark Background" data-select-class="dark-variant"/>
  <!-- Color picker for a CSS property -->
  <we-colorpicker string="Accent Color" data-select-style="true" data-css-property="--accent-color"/>
</div>
```

---

## Step 3: Add Custom Styles

Open `static/src/scss/snippet.scss`.

Scope ALL rules under `.s_{name}`:
```scss
.s_hero_split_screen {
  // your styles here

  &.dark-variant {
    background: #111;
    color: #fff;
  }
}
```

Good practices:
- Use CSS custom properties (`var(--color-primary)`) to inherit Odoo theme colors
- Use Bootstrap variables where possible (they're already loaded)
- Avoid `!important` — it breaks Odoo's inline style overrides in the editor
- File naming: `000.scss` prefix loads first; use `001.scss` for overrides if needed

---

## Step 4: Add JavaScript (if needed)

Open `static/src/js/snippet.js`.

For **Odoo 15–17** (OWL-based):
```javascript
import { Component } from '@odoo/owl';
import { registry } from '@web/core/registry';

class HeroSplitScreenSnippet extends Component {
    static template = xml`<t t-slot="default"/>`;
}

registry.category('public_components').add('hero_split_screen.HeroSplitScreenSnippet', {
    component: HeroSplitScreenSnippet,
});
```

For **simple vanilla JS** (counters, scroll effects — works all versions):
```javascript
document.addEventListener('DOMContentLoaded', () => {
    document.querySelectorAll('.s_hero_split_screen').forEach(el => {
        // your init code
    });
});
```

Leave `snippet.js` empty if no interactivity is needed.

---

## Step 5: Deploy the Module

Choose the appropriate deployment method:

### Option A: SSH / SFTP to server (self-hosted Odoo)
1. Copy `.tmp/snippets/hero_split_screen/` to the server's custom addons path
   - Typically: `/opt/odoo/custom-addons/` or `/usr/lib/python3/dist-packages/odoo/addons/`
2. Restart Odoo: `sudo systemctl restart odoo`
3. In Odoo: Settings → Technical → Update Apps List

### Option B: Odoo.sh (Odoo's cloud platform)
1. Add the module folder to your Odoo.sh git repository (custom branch)
2. Push the branch — Odoo.sh auto-deploys on push
3. Wait for the build to complete in Odoo.sh dashboard

### Option C: ZIP upload (some hosted Odoo plans)
1. Zip the module folder: `zip -r hero_split_screen.zip .tmp/snippets/hero_split_screen/`
2. In Odoo: Apps → Upload module → select ZIP
3. This option is only available if the instance has "Technical" mode enabled

### Option D: Local dev instance only
If testing locally before production:
1. Copy to your local Odoo addons path
2. Run: `./odoo-bin --dev=all -u hero_split_screen`
3. The `--dev=all` flag hot-reloads SCSS changes

---

## Step 6: Install and Verify

In Odoo:
1. Apps → search `hero_split_screen` → Install
   - If not found: Apps → Update Apps List first, then search again
2. Open the Website Editor → click the snippet panel (building blocks icon)
3. Scroll to the "Custom" category (or search by name)
4. Drag the snippet onto a test page
5. Verify it is editable (click on text regions in the editor)
6. Test on mobile breakpoint using the editor's responsive preview

---

## Troubleshooting

| Problem | Fix |
|---|---|
| Snippet doesn't appear in panel | Check `snippets_registration` XPath in `snippets.xml`; clear browser cache |
| SCSS not loading | Verify bundle name in `__manifest__.py` matches Odoo version (`web.assets_frontend`) |
| JS not executing | Check browser console for import errors; ensure OWL syntax matches Odoo version |
| Module not found after upload | Restart Odoo or run Settings → Technical → Update Apps List |
| Editor crashes when dropping snippet | Check for invalid XML in `snippets.xml` (unescaped `&`, unclosed tags) |
| Styles bleed to other elements | Ensure all rules in `snippet.scss` are scoped under `.s_{name}` |

---

## Notes
- For Odoo 15 and below, the bundle name in `assets.xml` is `website.assets_frontend` (not `web.assets_frontend`)
- Each snippet template id must be unique across all installed modules
- The `priority` attribute on the XPath (default `8`) controls snippet panel ordering — higher = later in the list
- Snippet option widgets (`we-select`, `we-checkbox`, etc.) are optional — the snippet works without them
