"""
Create or update an Odoo website page's HTML arch.

Usage:
    # Create a new page
    python3 tools/push_page.py --create --name "About Us" --url /about --file .tmp/draft_about.html

    # Update an existing page
    python3 tools/push_page.py --update --url /about --file .tmp/draft_about.html

    # Publish / unpublish
    python3 tools/push_page.py --publish --url /about
    python3 tools/push_page.py --unpublish --url /about
"""

import argparse
import os
import sys

sys.path.insert(0, os.path.dirname(__file__))
from odoo_client import OdooClient

QWEB_WRAPPER = """<t t-name="website.{key}">
  <t t-call="website.layout">
    <t t-set="pageName" t-value="'{name}'"/>
{content}
  </t>
</t>"""


def url_to_slug(url):
    return url.strip("/").replace("/", "_") or "home"


def wrap_arch(content, url, name):
    """Wrap raw HTML in QWeb template if not already wrapped."""
    content = content.strip()
    if content.startswith("<t t-name="):
        return content
    key = "page_" + url_to_slug(url)
    indented = "\n".join("    " + line for line in content.splitlines())
    return QWEB_WRAPPER.format(key=key, name=name.replace("'", "\\'"), content=indented)


def backup_existing(client, url, tmp_dir):
    """Fetch and save the current arch before overwriting. Returns view_id or None."""
    pages = client.search_read(
        "website.page",
        [("url", "=", url), ("active", "=", True)],
        ["id", "name", "url", "view_id"],
    )
    if not pages:
        return None

    page = pages[0]
    view_id = page["view_id"]
    if isinstance(view_id, (list, tuple)):
        view_id = view_id[0]

    views = client.read("ir.ui.view", [view_id], ["arch"])
    if views:
        slug = url_to_slug(url)
        backup_path = os.path.join(tmp_dir, f"backup_{slug}.html")
        with open(backup_path, "w", encoding="utf-8") as f:
            f.write(views[0]["arch"])
        print(f"Backup saved: .tmp/backup_{slug}.html")

    return view_id, page["id"]


def cmd_create(client, args, tmp_dir):
    if not args.name:
        sys.exit("ERROR: --name is required for --create")

    arch = wrap_arch(args.content, args.url, args.name)

    # Check for duplicate URL
    existing = client.search_read(
        "website.page", [("url", "=", args.url)], ["id", "name"]
    )
    if existing:
        print(
            f"WARNING: A page already exists at {args.url} (ID {existing[0]['id']}).\n"
            "Use --update to modify it instead."
        )
        sys.exit(1)

    # Create ir.ui.view first
    key = f"website.page_{url_to_slug(args.url)}"
    view_id = client.create(
        "ir.ui.view",
        {
            "name": args.name,
            "type": "qweb",
            "key": key,
            "arch": arch,
        },
    )
    print(f"Created ir.ui.view ID: {view_id}")

    # Create website.page linked to the view
    page_id = client.create(
        "website.page",
        {
            "name": args.name,
            "url": args.url,
            "view_id": view_id,
            "website_published": False,
            "is_homepage": False,
        },
    )
    print(f"Created website.page ID: {page_id}  |  URL: {args.url}")
    print(f"Page is UNPUBLISHED. Run --publish to make it live.")


def cmd_update(client, args, tmp_dir):
    result = backup_existing(client, args.url, tmp_dir)
    if result is None:
        sys.exit(
            f"ERROR: No page found at {args.url}. Use --create to make a new page."
        )

    view_id, page_id = result

    # Get page name for QWeb wrapper
    pages = client.read("website.page", [page_id], ["name"])
    name = pages[0]["name"] if pages else url_to_slug(args.url)

    arch = wrap_arch(args.content, args.url, name)
    client.write("ir.ui.view", [view_id], {"arch": arch})
    print(f"Updated view ID {view_id} for page at {args.url}")


def cmd_publish(client, url, publish):
    pages = client.search_read(
        "website.page", [("url", "=", url), ("active", "=", True)], ["id", "name"]
    )
    if not pages:
        sys.exit(f"ERROR: No page found at {url}")
    page_id = pages[0]["id"]
    client.write("website.page", [page_id], {"website_published": publish})
    state = "published" if publish else "unpublished"
    print(f"Page '{pages[0]['name']}' ({url}) is now {state}.")


def main():
    parser = argparse.ArgumentParser(description="Push HTML to an Odoo website page")

    mode = parser.add_mutually_exclusive_group(required=True)
    mode.add_argument("--create", action="store_true", help="Create a new page")
    mode.add_argument("--update", action="store_true", help="Update an existing page")
    mode.add_argument("--publish", action="store_true", help="Publish a page")
    mode.add_argument("--unpublish", action="store_true", help="Unpublish a page")

    parser.add_argument("--url", required=True, help="Page URL (e.g. /about)")
    parser.add_argument("--name", help="Page name (required for --create)")
    parser.add_argument("--file", help="Path to HTML file (required for --create/--update)")

    args = parser.parse_args()

    tmp_dir = os.path.join(os.path.dirname(__file__), "..", ".tmp")
    os.makedirs(tmp_dir, exist_ok=True)

    client = OdooClient()

    if args.create or args.update:
        if not args.file:
            sys.exit("ERROR: --file is required for --create and --update")
        if not os.path.exists(args.file):
            sys.exit(f"ERROR: File not found: {args.file}")
        with open(args.file, "r", encoding="utf-8") as f:
            args.content = f.read()

    if args.create:
        cmd_create(client, args, tmp_dir)
    elif args.update:
        cmd_update(client, args, tmp_dir)
    elif args.publish:
        cmd_publish(client, args.url, publish=True)
    elif args.unpublish:
        cmd_publish(client, args.url, publish=False)


if __name__ == "__main__":
    main()
