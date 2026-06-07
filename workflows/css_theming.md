# CSS Theming Workflow

## Objective

Reference SOP for pushing CSS to any Odoo page via `website.custom_code_head`. Use this when a page has contrast issues, default Odoo colors, or mismatched styling — without touching page arch.

---

## The Tool (use this — don't write raw RPC calls)

```bash
python3 tools/push_css.py --block-name <name> --file .tmp/<name>.css
python3 tools/push_css.py --block-name <name> --file .tmp/<name>.css --dry-run
```

- CSS file contains **raw CSS only** — no `<style>` tags (the tool wraps them)
- Block names in use: `header`, `shop`, `pages`, `forms`, `footer`
- Re-running is safe — idempotent block replacement via regex markers
- Rollback: push an empty file → `echo "" > .tmp/empty.css && python3 tools/push_css.py --block-name <name> --file .tmp/empty.css`

---

## The Mechanism

All global CSS lives in one field on the `website` model, injected into every page's `<head>`:

```python
# Read
sites = c.search_read("website", [], ["id", "custom_code_head"])
head = sites[0].get("custom_code_head") or ""

# Write
c.write("website", [site_id], {"custom_code_head": new_head})
```

---

## Active CSS Blocks (19prince staging, website ID 3)

| Block name | File | Scope | Purpose |
|---|---|---|---|
| `header` | `.tmp/header.css` | Site-wide | Solid dark navy header on all pages |
| `shop` | `.tmp/shop.css` | `.oe_website_sale` + `#wrapwrap` | Light grid background, white product cards, blue prices |
| `pages` | `.tmp/pages.css` | `#wrap.website_blog`, `section.s_title` | Blog light bg, title banner blueprint grid |
| `forms` | `.tmp/forms.css` | `.s_website_form_label`, `.form-control` | Global form labels (bold/dark), inputs (`#F1F2F6` bg) |
| `footer` | `.tmp/footer.css` | `footer#bottom` | Dark navy footer, orange accent bar, LinkedIn icon |

---

## Confirmed Selector Map

### Global / Header
| Target | Selector | Notes |
|---|---|---|
| Header bar | `header#top`, `header#top .navbar` | Must use `!important` — Odoo theme overrides |
| Page background (all pages) | `#wrapwrap` | Set in `shop` block — applies globally |
| Title banners (`s_title` sections) | `section.s_title`, `section.s_title.bg-black-50` | `bg-black-50` is the default Odoo dark class |

### eCommerce Shop (`/shop`)
| Target | Selector |
|---|---|
| Main wrapper | `.oe_website_sale` |
| Product cards | `.oe_website_sale .oe_product_cart` |
| Image container | `.oe_website_sale .o_product_image`, `.oe_website_sale .oe_product_image` |
| Product name | `.oe_website_sale h5.product_name`, `.ee_website_sale .product_name` |
| Price | `.ee_website_sale .oe_currency_value`, `.oe_website_sale .oe_price` |
| Left sidebar | `.oe_website_sale .o_wsale_sidebar`, `.oe_website_sale #wsale_category_dropdown` |
| Search/sort bar | `.ee_website_sale #o_wsale_products_header` |
| Layout toggle | `.oe_website_sale .o_wsale_layout_btn` |
| Pagination | `.oe_website_sale .page-link` |

### Blog Listing (`/blog/*`)
| Target | Selector | Notes |
|---|---|---|
| **Body wrap** | `#wrap.website_blog` | ⚠️ NOT `body.o_wblog_index` — body has no class |
| All sections (clear dark bg) | `#wrap.website_blog section`, `#wrap.website_blog .o_colored_level`, `#wrap.website_blog .o_wblog_page_cards_bg` | Must clear these or dark bg bleeds through |
| Cards content area | `#o_wblog_index_content` | Has class `o_wblog_page_cards_bg` |
| Post cards | `.o_wblog_index .card`, `.o_blog_post_teaser .card` | |
| Card titles | `.o_wblog_index .card-title`, `.o_wblog_index .card-title a` | |
| Card text | `.o_wblog_index .card-text`, `.o_wblog_index .card-body p` | |
| Card footer | `.o_wblog_index .card-footer` | |
| Muted text | `.o_wblog_index .text-muted`, `.o_wblog_index small` | |
| Badges | `.o_wblog_index .badge` | |
| Sidebar | `.o_wblog_index aside`, `.o_wblog_index .o_wblog_sidebar` | |
| Pagination | `.o_wblog_index .page-link` | |

### Contact Page (`/contactus`)
| Target | Selector | Notes |
|---|---|---|
| Title banner | `section.s_title.bg-black-50` | Odoo default dark class on `s_title` sections |
| Content sections | `section.s_text_block.o_colored_level` | Set `background: transparent` |
| Form labels | `.s_website_form_label`, `.s_website_form_label_content`, `.col-form-label` | Global — in `forms` block |
| Form inputs | `.s_website_form_input.form-control`, `#contactus_form input/textarea` | |
| Submit button | `#contactus_form .btn-primary` | |
| ⚠️ No body class | — | `/contactus` body has no page-specific class. Scope by `#contactus_form` or `section.s_title.bg-black-50` |

### Footer
| Target | Selector | Notes |
|---|---|---|
| Main footer | `footer#bottom`, `footer#bottom .o_colored_level`, `footer#bottom section` | |
| Orange divider bar | `footer#bottom::before` | 2px, 90% width, 15px from top via `margin: 15px auto 0` |
| Inner content div | `footer#bottom #footer` | `padding-top: 20px` to push below bar |
| Brand heading | `footer#bottom h4`, `footer#bottom h4 b` | |
| Body text | `footer#bottom p` | |
| Links | `footer#bottom a` | |
| Subscribe input | `footer#bottom input.js_subscribe_value` | |
| Subscribe button | `footer#bottom .js_subscribe_btn`, `footer#bottom .btn-primary` | |
| LinkedIn icon | `footer#bottom .fa-linkedin` | FontAwesome `i` element, style with bg + padding |
| Copyright strip | `.o_footer_copyright`, `footer .o_footer_copyright` | |

### Global Forms (site-wide)
| Target | Selector |
|---|---|
| Labels | `.s_website_form_label`, `.s_website_form_label_content`, `.col-form-label` |
| Required mark (*) | `.s_website_form_mark` |
| All inputs | `.form-control`, `input.form-control`, `textarea.form-control` |
| Focus state | `.form-control:focus` |
| Submit buttons | `.s_website_form .btn-primary`, `.o_website_form_send` |

---

## Design Decisions (19prince)

| Decision | Value | Rationale |
|---|---|---|
| Brand orange | `#EB6B08` | Used on footer divider bar, CTA accents |
| Light page bg | `#f4f6f9` with 32px light grid | Shop, blog, contact pages |
| Light grid lines | `rgba(0,0,0,.035)` | Very subtle on light pages |
| Dark page bg | `#071222` | Homepage, header, footer — blueprint theme |
| Dark grid lines | `rgba(59,142,234,.07)` at 28px | Blueprint grid on dark surfaces |
| Form input bg | `#F1F2F6` | Slight off-white to distinguish from page bg |
| Title banners | Dark navy `#071222` + blueprint grid + white text | All `section.s_title` globally |
| Footer style | Dark navy bookend + `#EB6B08` orange divider bar | Contrasts both light and dark pages |

---

## Block Management Pattern

Each CSS block is wrapped with named markers so re-pushing replaces without duplication:

```css
/* == block-name start == */
/* ... rules ... */
/* == block-name end == */
```

**Critical:** Markers must be CSS comments _inside_ `<style>` tags — never bare HTML text.

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
| Brand orange | `#EB6B08` |
| Success | `#4ade80` |
| Error | `#f87171` |
| Warning | `#fbbf24` |

---

## Blueprint Grid Pattern

**Dark surfaces** (header, title banners, footer):
```css
background-image:
  linear-gradient(rgba(59,142,234,.07) 1px, transparent 1px),
  linear-gradient(90deg, rgba(59,142,234,.07) 1px, transparent 1px);
background-color: #071222;
background-size: 28px 28px;
```

**Light surfaces** (shop, blog, contact):
```css
background-image:
  linear-gradient(rgba(0,0,0,.035) 1px, transparent 1px),
  linear-gradient(90deg, rgba(0,0,0,.035) 1px, transparent 1px);
background-color: #f4f6f9;
background-size: 32px 32px;
```

---

## Rules

1. **Always scope selectors** — never write unscoped rules like `h1 { color: white }`
2. **Use `!important`** on color and background overrides — Odoo's specificity is very high
3. **Never edit `ir.ui.view` arch** for styling — CSS only via `custom_code_head`
4. **Use `push_css.py` tool** — never write raw RPC calls for CSS
5. **Verify with a screenshot** — ask user to refresh after every push
6. **Fetch rendered HTML** to find real selectors when in doubt: `python3 -c "import requests,re,os; from dotenv import load_dotenv; load_dotenv(); r=requests.get(os.getenv('ODOO_URL')+'/your-path'); print(re.search(r'<body[^>]*>',r.text).group(0))"`

---

## Troubleshooting

| Problem | Fix |
|---|---|
| Style not applying | Raise specificity: add parent selector, or fetch rendered HTML to find real class names |
| Body class doesn't exist | Many Odoo pages have no body-level page class — scope by `#wrap.{page-class}` or a unique element ID |
| Dark section bleeding through on light page | Target `.o_colored_level` and `section` within the page wrapper and set `background: transparent !important` |
| Style applying everywhere | Selector too broad — scope it further |
| Stale styles showing | Odoo asset cache — add `?nocache=1` to URL or clear via Settings → Technical |
| Marker text visible on page | Markers placed outside `<style>` tag — move them inside as CSS comments |
| `custom_code_head` write fails | Check that `website` model write access is granted to the user |
