# Create Mailing Workflow

## Objective

Format structured markdown content into an Odoo email mailing using an existing mailing as the HTML template, then push as a draft.

## Required Inputs

- Source markdown file with frontmatter (`subject`, `date`) and H2-delimited sections
- `.env` populated with: `ODOO_URL`, `ODOO_DB`, `ODOO_USER`, `ODOO_PASSWORD`

---

## Markdown Format

The source markdown must follow this structure:

```markdown
---
subject: "Your email subject line"
date: April 29, 2026
---

## Section Name

Paragraphs, **bold text**, [links](url), bullet lists...

### Sub-heading

Content within the same section...

## Another Section

Next section's content.
```

### Mapping Rules

| Markdown | HTML Output |
|----------|-------------|
| Frontmatter `subject` | Mailing subject line |
| Frontmatter `date` | Right-aligned date in the header |
| `## H2 Heading` | Section banner (colored bar with heading) |
| Content under H2 | Text block following the banner |
| `### H3 Heading` | `<h5>` sub-heading within the text block |
| `**bold lead.**` at paragraph start | `<strong>` lead phrase |
| `[text](url)` | `<a href="url">text</a>` |
| `- item` | `<ul><li>` list |
| `*italic*` | `<em>` |

---

## Steps

### 1. Verify credentials

Open `.env` and confirm all four Odoo keys are set. If any are blank:
- Stop here and ask the user to provide them
- Do NOT attempt to connect with placeholder values

### 2. Read the source markdown

Read the user's markdown file. Confirm it has:
- Frontmatter with at least a `subject` field
- One or more `## H2` section headings

Print the section structure found (list of H2 headings) so the user can confirm the content is correct.

### 3. Select a template mailing

Run:
```bash
python3 tools/list_mailings.py --mailings
```

Ask the user: **"Which mailing should I use as the HTML template?"**

If the user doesn't know, suggest the most recent mailing with state `done`. The template determines the visual style, header/footer chrome, and section pattern used in the output.

### 4. Fetch the template

```bash
python3 tools/get_mailing.py --id <selected_id>
```

Read the saved body_arch file from `.tmp/mailing_<id>_body_arch.html`.

### 5. Analyze the template structure

Identify the repeating patterns in the template HTML:

- **Header block**: Date, headline text, logo/image. Look for the first `s_picture` or similar snippet before any section banners.
- **Section pairs**: Each section is a banner element (`s_title` with a colored background class like `bg-o-color-1`) followed by a text block (`s_text_block` with content). Note the exact CSS classes, `data-snippet` values, and nesting structure.
- **Footer block**: Social links, unsubscribe/contact links, copyright. Look for `s_footer_social` or `o_mail_block_footer_social`.

### 6. Map markdown to template

For each `## H2` section in the markdown:
1. Clone the template's banner + text block pattern
2. Set the banner heading text to the H2 text
3. Convert the markdown content under that H2 to HTML and place it in the text block
4. Preserve the header block from the template, updating:
   - The date from frontmatter
   - The headline from frontmatter `subject` (or the first H1 if present)
5. Preserve the footer block unchanged

**Section count rules:**
- If the markdown has **more** sections than the template, repeat the last banner + text block pattern for additional sections
- If the markdown has **fewer** sections, omit the extra template sections

### 7. Write the output

Save to `.tmp/draft_mailing.html`.

### 8. Validate

```bash
python3 tools/validate_html.py --input .tmp/draft_mailing.html
```

- **Errors**: Must be fixed before pushing
- **Warnings**: Review but acceptable (the `o_editable` and `t-name` warnings are expected for email arches)

### 9. Confirm with user

Before touching the live system, confirm:

> "Ready to create a draft mailing with subject '[subject]' on [ODOO_URL]. This will NOT send the email. Proceed?"

### 10. Push as draft

Determine which mailing list to target:
```bash
python3 tools/list_mailings.py --lists
```

Push the mailing:
```bash
python3 tools/push_mailing.py --create \
  --subject "Your subject line" \
  --file .tmp/draft_mailing.html \
  --list-id <N>
```

The mailing is created as a **draft**. It will NOT be sent automatically. Print the Odoo URL so the user can review the mailing in the Odoo backend before sending.

---

## Updating an Existing Mailing

To update a mailing that was already pushed:

```bash
python3 tools/push_mailing.py --update \
  --id <mailing_id> \
  --file .tmp/draft_mailing.html
```

This creates a backup of the current body_arch before overwriting.

---

## Error Reference

| Error message | Cause | Fix |
|---|---|---|
| `No mailings found` | Email Marketing module is empty | Create a mailing manually in Odoo first, then use it as a template |
| `No mailing found with ID X` | Wrong ID selected | Run `list_mailings.py` to see current IDs |
| `No mailing lists found` | No lists created yet | Create a mailing list in Odoo Email Marketing first |
| `Model 'mailing.list' not found` | Email Marketing module not installed | Install the Email Marketing app in Odoo |
| `Authentication failed` | Wrong credentials | Check `ODOO_USER` and `ODOO_PASSWORD` in `.env` |
| `ODOO_URL uses plain HTTP` | Insecure connection | Switch to `https://` or set `ODOO_ALLOW_HTTP=true` in `.env` |
