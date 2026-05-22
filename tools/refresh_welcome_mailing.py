"""
Refresh the welcome mailing with the latest 3 Newsletter-tagged blog posts.

Reads .tmp/welcome_email.html as the base template, fetches the 3 most recent
published posts tagged "Newsletter" from Odoo, injects them into the
BLOG_POSTS_SLOT comment, then pushes the result to mailing ID 23 as a draft.

Usage:
    python3 tools/refresh_welcome_mailing.py
    python3 tools/refresh_welcome_mailing.py --mailing-id 25   # different mailing
    python3 tools/refresh_welcome_mailing.py --dry-run          # print HTML, no push
"""

import argparse
import html
import os
import re
import sys

sys.path.insert(0, os.path.dirname(__file__))
from odoo_client import OdooClient

TEMPLATE_PATH = os.path.join(os.path.dirname(__file__), "..", ".tmp", "welcome_email.html")
SLOT_START    = "<!-- BLOG_POSTS_SLOT:START -->"
SLOT_END      = "<!-- BLOG_POSTS_SLOT:END -->"
WEBSITE_BASE  = "https://www.19prince.com"
LABELS        = ["01 &nbsp;&middot;&nbsp; LATEST", "02 &nbsp;&middot;&nbsp; PREVIOUS", "03 &nbsp;&middot;&nbsp; EARLIER"]

MONO  = "'JetBrains Mono', 'SF Mono', Menlo, Consolas, monospace"
SANS  = "'Inter Tight', -apple-system, BlinkMacSystemFont, system-ui, sans-serif"


def clean_teaser(raw: str, title: str) -> str:
    """Strip zero-width spaces, leading date/title echo, return ~160 chars."""
    # Remove zero-width spaces and non-breaking spaces run-ons
    text = re.sub(r'[​‌‍﻿]+', ' ', raw or '')
    text = re.sub(r'\s+', ' ', text).strip()

    # Strip leading title echo (posts often start with the full title)
    if text.startswith(title):
        text = text[len(title):].strip()

    # Strip leading date patterns like "April 29, 2026" or "May 19, 2026"
    text = re.sub(r'^[A-Z][a-z]+ \d{1,2},?\s+\d{4}\s*', '', text).strip()

    # Strip leading TL;DR header if it crept in
    text = re.sub(r'^TL;DR\s*', '', text, flags=re.IGNORECASE).strip()

    # Trim to ~160 chars at a word boundary
    if len(text) > 160:
        text = text[:160].rsplit(' ', 1)[0] + '...'

    return text or 'Read the full post on the 19 Prince blog.'


def render_post_slot(index: int, title: str, teaser: str, url: str, is_last: bool) -> str:
    label = LABELS[index]
    full_url = WEBSITE_BASE + url

    if is_last:
        cell_style = 'padding-top: 24px;'
    elif index == 0:
        cell_style = 'padding-bottom: 24px; border-bottom: 1px solid #e9edf3;'
    else:
        cell_style = 'padding: 24px 0; border-bottom: 1px solid #e9edf3;'

    safe_title  = html.escape(title)
    safe_teaser = html.escape(teaser)

    return f"""        <table width="100%" cellpadding="0" cellspacing="0" border="0" style="border-collapse: collapse;">
            <tr>
                <td style="{cell_style}">
                    <p style="font-family: {MONO}; font-size: 10px; font-weight: 500; letter-spacing: .12em; text-transform: uppercase; color: #a9b3c2; margin: 0 0 8px 0;">{label}</p>
                    <p style="font-family: {SANS}; font-weight: 700; font-size: 18px; line-height: 1.2; letter-spacing: -0.02em; color: #071222; margin: 0 0 8px 0;">{safe_title}</p>
                    <p style="font-family: {SANS}; font-weight: 400; font-size: 14px; line-height: 1.55; color: #525c6d; margin: 0 0 12px 0;">{safe_teaser}</p>
                    <a href="{full_url}" style="font-family: {SANS}; font-size: 13px; font-weight: 600; color: #EA6C08; text-decoration: none; letter-spacing: -0.01em;">Read &#8594;</a>
                </td>
            </tr>
        </table>
"""


def build_posts_block(posts: list) -> str:
    slots = []
    for i, post in enumerate(posts):
        title  = post.get('name') or ''
        raw    = post.get('teaser') or ''
        teaser = clean_teaser(raw, title)
        url    = post.get('website_url') or '/'
        slots.append(render_post_slot(i, title, teaser, url, is_last=(i == len(posts) - 1)))

    inner = '\n'.join(slots)
    return f"""<div class="s_text_block o_mail_snippet_general" style="background-color: #ffffff; padding: 0 32px 40px;" data-snippet="s_text_block" data-name="RecentPosts">
    <div class="container s_allow_columns">

        <hr style="border: 0; border-top: 1px solid #d3dae4; margin: 0 0 32px 0;">

        <p style="font-family: {MONO}; font-size: 11px; font-weight: 500; letter-spacing: .16em; text-transform: uppercase; color: #5DA9FF; margin: 0 0 28px 0;">RECENT POSTS</p>

{inner}
    </div>
</div>"""


def main():
    parser = argparse.ArgumentParser(description="Refresh welcome mailing with latest blog posts")
    parser.add_argument('--mailing-id', type=int, default=23, dest='mailing_id',
                        help='Odoo mailing ID to update (default: 23)')
    parser.add_argument('--limit', type=int, default=3,
                        help='Number of posts to include (default: 3)')
    parser.add_argument('--dry-run', action='store_true',
                        help='Print rendered HTML without pushing to Odoo')
    args = parser.parse_args()

    # Load base template
    if not os.path.exists(TEMPLATE_PATH):
        sys.exit(f"ERROR: Template not found: {TEMPLATE_PATH}")
    with open(TEMPLATE_PATH, 'r', encoding='utf-8') as f:
        template = f.read()

    if SLOT_START not in template or SLOT_END not in template:
        sys.exit(f"ERROR: Slot markers not found in template. Expected {SLOT_START!r} and {SLOT_END!r}")

    # Fetch blog posts
    client = OdooClient()
    posts = client.search_read(
        'blog.post',
        [('website_published', '=', True), ('tag_ids.name', 'ilike', 'newsletter')],
        ['id', 'name', 'teaser', 'post_date', 'website_url'],
        limit=args.limit,
    )

    if not posts:
        sys.exit("ERROR: No published posts with tag 'newsletter' found.")

    posts.sort(key=lambda p: p.get('post_date') or '', reverse=True)
    posts = posts[:args.limit]

    print(f"Found {len(posts)} post(s):")
    for p in posts:
        print(f"  {p['post_date'][:10]}  {p['name'][:60]}")

    # Build and inject
    posts_block = build_posts_block(posts)
    body = re.sub(
        r'<!-- BLOG_POSTS_SLOT:START -->.*?<!-- BLOG_POSTS_SLOT:END -->',
        f'{SLOT_START}\n{posts_block}\n{SLOT_END}',
        template,
        flags=re.DOTALL,
    )

    if args.dry_run:
        out_path = os.path.join(os.path.dirname(__file__), '..', '.tmp', 'welcome_email_preview.html')
        with open(out_path, 'w', encoding='utf-8') as f:
            f.write(body)
        print(f"\nDry run — rendered HTML saved to: .tmp/welcome_email_preview.html")
        return

    # Push to Odoo
    records = client.read('mailing.mailing', [args.mailing_id], ['id', 'subject', 'state'])
    if not records:
        sys.exit(f"ERROR: Mailing ID {args.mailing_id} not found.")

    mailing = records[0]
    client.write('mailing.mailing', [args.mailing_id], {
        'body_arch': body,
        'body_html': body,
    })

    print(f"\nUpdated mailing ID: {args.mailing_id}")
    print(f"Subject: {mailing['subject']}")
    print(f"State: {mailing['state']} (draft — will not send automatically)")
    print(f"\nView in Odoo: {client.url}/web#id={args.mailing_id}&model=mailing.mailing&view_type=form")


if __name__ == '__main__':
    main()
