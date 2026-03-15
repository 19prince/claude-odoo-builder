"""
Fetch the HTML arch of an Odoo website page and save it locally.
Always creates a backup before any editing session.

Usage:
    python3 tools/get_page.py --url /about
    python3 tools/get_page.py --id 42
"""

import argparse
import os
import sys

sys.path.insert(0, os.path.dirname(__file__))
from odoo_client import OdooClient


def url_to_slug(url):
    """Convert /about-us to about-us for use in filenames."""
    return url.strip("/").replace("/", "_") or "home"


def fetch_page_arch(client, url=None, page_id=None):
    """Return (page_record, arch_string) or raise RuntimeError."""
    if url:
        pages = client.search_read(
            "website.page",
            [("url", "=", url), ("active", "=", True)],
            ["id", "name", "url", "view_id", "website_published"],
        )
        if not pages:
            raise RuntimeError(f"No page found with URL: {url}")
        page = pages[0]
    elif page_id:
        records = client.read("website.page", [page_id], ["id", "name", "url", "view_id", "website_published"])
        if not records:
            raise RuntimeError(f"No page found with ID: {page_id}")
        page = records[0]
    else:
        raise ValueError("Provide --url or --id")

    view_id = page["view_id"]
    if isinstance(view_id, (list, tuple)):
        view_id = view_id[0]

    views = client.read("ir.ui.view", [view_id], ["id", "name", "arch", "key"])
    if not views:
        raise RuntimeError(f"View {view_id} not found for page {page['name']}")

    return page, views[0]["arch"]


def main():
    parser = argparse.ArgumentParser(description="Fetch an Odoo page's HTML arch")
    group = parser.add_mutually_exclusive_group(required=True)
    group.add_argument("--url", help="Page URL (e.g. /about)")
    group.add_argument("--id", type=int, dest="page_id", help="Page record ID")
    parser.add_argument("--no-backup", action="store_true", help="Skip saving backup file")
    args = parser.parse_args()

    client = OdooClient()
    page, arch = fetch_page_arch(client, url=args.url, page_id=args.page_id)

    slug = url_to_slug(page["url"] or str(page["id"]))
    tmp_dir = os.path.join(os.path.dirname(__file__), "..", ".tmp")
    os.makedirs(tmp_dir, exist_ok=True)

    if not args.no_backup:
        backup_path = os.path.join(tmp_dir, f"page_{slug}.html")
        with open(backup_path, "w", encoding="utf-8") as f:
            f.write(arch)
        print(f"Saved to: .tmp/page_{slug}.html")

    print(f"\n--- Page: {page['name']} ({page['url']}) ---")
    print(f"ID: {page['id']}  |  View ID: {page['view_id']}  |  Published: {page['website_published']}")
    print("\n--- arch ---")
    print(arch)


if __name__ == "__main__":
    main()
