# CSS Theming Workflow

## Objective

Reference SOP for pushing blueprint dark theme CSS to any Odoo page via `website.custom_code_head`. Use this when a page has contrast issues, default Odoo colors, or mismatched styling — without touching page arch.

---

## The Mechanism

All global CSS lives in one field on the `website` model:

```python
# Read
sites = c.search_read("website", [], ["id", "custom_code_head"])
head = sites[0].get("custom_code_head") or ""

# Write
c.write("website", [site_id], {"custom_code_head": new_head})
```

This injects into every page's `<head>`. Scope all rules to a page-level class to avoid unintended bleed.

---

## Confirmed Selector Map

Selectors confirmed working against `https://example-project.odoo.com` (Odoo 17 SaaS).

### Global / Header
| Target | Selector |
|---|---|
| Header bar | `header#top`, `header#top .navbar` |
| Nav links | `header#top .navbar-nav .nav-link` |
| Dropdown menu | `header#top .dropdown-menu` |
| Dropdown items | `header#top .dropdown-item` |
| CTA button | `header#top .btn_cta`, `header#top a.btn_cta` |
| Mobile toggler | `header#top .navbar-toggler` |
| Offcanvas drawer | `#o_offcanvas_menu` |
| Page background | `body` |

### Blog Listing Page (`.o_wblog_index`)
| Target | Selector |
|---|---|
| Page wrapper | `.o_wblog_index` |
| Blog cover / header | `.o_wblog_index .o_blog_header` |
| Blog name h1 | `.o_wblog_index .o_blog_name`, `.o_wblog_index h1` |
| Blog subtitle | `.o_wblog_index .o_blog_subtitle` |
| Search bar strip | `.o_wblog_index .o_wblog_search_form` |
| Search input | `.o_wblog_index input[type="search"]` |
| Post cards | `.o_wblog_index .card`, `.o_blog_post_teaser .card` |
| Card thumbnail area | `.o_wblog_index .o_record_has_cover`, `.o_wblog_index figure` |
| Card titles | `.o_wblog_index .card-title`, `.o_wblog_index .card-title a` |
| Card excerpt | `.o_wblog_index .card-text`, `.o_wblog_index .card-body p` |
| Card footer | `.o_wblog_index .card-footer` |
| Date / muted text | `.o_wblog_index .text-muted`, `.o_wblog_index small` |
| Tags / badges | `.o_wblog_index .badge` |
| Pagination | `.o_wblog_index .page-link` |
| Active page | `.o_wblog_index .page-item.active .page-link` |
| Sidebar | `.o_wblog_index aside`, `.o_wblog_index .o_wblog_sidebar` |

### Blog Post Page (`.o_wblog_post_page`)
| Target | Selector |
|---|---|
| Post header / cover | `.o_wblog_post_page .o_blog_header` |
| Post title (h1) | `h1.o_blog_post_title`, `.o_wblog_post_page h1` |
| Post subtitle | `.o_blog_post_subtitle`, `.o_wblog_post_page .o_blog_post_subtitle` |
| Content area | `.o_wblog_post_page #o_wblog_post_content` |
| Editable content | `.website_blog_post .o_editable` |

### Website Pages (general)
| Target | Selector |
|---|---|
| Page content wrapper | `.o_editable` (scoped to page URL class if needed) |
| Standard sections | `.o_colored_level`, `.s_banner`, `.s_text_block` |

---

## Block Management Pattern

Each thematic section gets its own named block. Use `re.sub` to replace, never append duplicates:

```python
import re

MARKER_START = "/* == my-section start == */"
MARKER_END   = "/* == my-section end == */"

# Strip old block
head = re.sub(
    r'/\* == my-section start == \*/.*?/\* == my-section end == \*/',
    '', head, flags=re.DOTALL
).strip()

NEW_CSS = """<style>
/* == my-section start == */
/* ... rules ... */
/* == my-section end == */
</style>"""

new_head = head + "\n" + NEW_CSS.strip()
```

**Critical:** Markers must be CSS comments _inside_ `<style>` tags. Never place them as bare text in the HTML — they will render visibly on the page.

---

## Blueprint Palette

| Role | Value |
|---|---|
| Page background | `#071222` |
| Card / panel | `rgba(10,28,51,.85)` |
| Elevated surface | `#0a1c33` |
| Primary blue | `#3b8eea` |
| Bright blue | `#5da8ff` |
| Light blue (muted) | `#7ec8ff` |
| Heading text | `#ffffff` |
| Body text | `rgba(255,255,255,.82)` |
| Muted text | `rgba(255,255,255,.55)` |
| Subtle text | `rgba(255,255,255,.4)` |
| Card border | `rgba(59,142,234,.22)` |
| Divider | `rgba(59,142,234,.18)` |
| Blueprint grid | `rgba(59,142,234,.07)` |
| Success | `#4ade80` |
| Error | `#f87171` |
| Warning | `#fbbf24` |

---

## Blueprint Grid Pattern

Use on any dark surface that needs texture (card thumbnails, hero backgrounds):

```css
background-image:
  linear-gradient(rgba(59,142,234,.07) 1px, transparent 1px),
  linear-gradient(90deg, rgba(59,142,234,.07) 1px, transparent 1px);
background-color: #071e35;
background-size: 28px 28px;
```

---

## Rules

1. **Always scope selectors** to a page-level class — never write unscoped rules like `h1 { color: white }`
2. **Use `!important`** on color and background overrides — Odoo's specificity is very high
3. **Never edit `ir.ui.view` arch** for styling — CSS only via `custom_code_head`
4. **Strip before append** — always use `re.sub` to remove the previous block for a section before adding the new one
5. **Verify with a screenshot** — ask the user to refresh and share a screenshot after every push

---

## Troubleshooting

| Problem | Fix |
|---|---|
| Style not applying | Raise specificity: add parent class, or duplicate the selector |
| Style applying everywhere | Selector too broad — scope it to the page body class |
| Stale styles showing | Odoo asset cache — ask user to add `?nocache=1` to URL or clear via Settings → Technical |
| Marker text visible on page | Markers placed outside `<style>` tag — move them inside as CSS comments |
| `custom_code_head` write fails | Check that `website` model write access is granted to the user |
