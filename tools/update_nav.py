"""
Create, update, or delete website.menu items for the 19prince nav.

Usage:
    python3 tools/update_nav.py --list
    python3 tools/update_nav.py --list --prod
    python3 tools/update_nav.py --restructure --dry-run
    python3 tools/update_nav.py --restructure --prod --dry-run
    python3 tools/update_nav.py --restructure --prod
    python3 tools/update_nav.py --set-mega --menu-id 99 --file .tmp/mega_resources.html
    python3 tools/update_nav.py --set-mega --menu-id 99 --file .tmp/mega_resources.html --prod
"""

import argparse
import json
import os
import sys
from urllib.parse import urlparse

from dotenv import load_dotenv

load_dotenv(os.path.join(os.path.dirname(__file__), "..", ".env"))

sys.path.insert(0, os.path.dirname(__file__))
from odoo_client import OdooClient

STAGING_WEBSITE_ID = 3
STAGING_TOP_MENU_ID = 14

DESIRED_ITEMS = [
    {"name": "About",          "url": "/about",      "sequence": 10},
    {"name": "Blog",           "url": "/blog",       "sequence": 20},
    {"name": "Resources",      "url": "#",           "sequence": 30},  # mega-menu parent
]


def get_client(prod=False):
    if prod:
        raw_url = os.getenv("PROD_ODOO_URL", "").rstrip("/")
        parsed = urlparse(raw_url)
        prod_url = f"{parsed.scheme}://{parsed.netloc}"
        return OdooClient(
            url=prod_url,
            db=os.getenv("PROD_ODOO_DB", ""),
            user=os.getenv("PROD_ODOO_USER", ""),
            password=os.getenv("PROD_ODOO_PASSWORD", ""),
        )
    return OdooClient()


def get_ids(client, prod=False, website_id=None, top_menu_id=None):
    if website_id and top_menu_id:
        return website_id, top_menu_id
    if prod:
        sites = client.search_read("website", [], ["id", "name"])
        ws_id = sites[0]["id"]
        roots = client.search_read(
            "website.menu",
            [("website_id", "=", ws_id), ("parent_id", "=", False)],
            ["id"],
        )
        tm_id = roots[0]["id"] if roots else None
        if not tm_id:
            sys.exit("ERROR: Could not find root menu on production")
        return ws_id, tm_id
    return STAGING_WEBSITE_ID, STAGING_TOP_MENU_ID


def list_items(client, top_menu_id):
    items = client.search_read(
        "website.menu",
        [["parent_id", "=", top_menu_id]],
        ["id", "name", "url", "sequence", "mega_menu_content"],
    )
    print(f"\nCurrent nav items under menu ID {top_menu_id}:")
    for item in sorted(items, key=lambda x: x["sequence"]):
        has_mega = "YES" if item["mega_menu_content"] else "no"
        print(f"  [{item['id']}] seq={item['sequence']:3d}  mega={has_mega}  {item['name']!r}  →  {item['url']}")
    print()
    return items


def restructure(client, website_id, top_menu_id, dry_run=False):
    existing = client.search_read(
        "website.menu",
        [["parent_id", "=", top_menu_id]],
        ["id", "name"],
    )
    existing_ids = [e["id"] for e in existing]

    if dry_run:
        print(f"[dry-run] Would delete {len(existing_ids)} existing items: {existing_ids}")
        print("[dry-run] Would create:")
        for item in DESIRED_ITEMS:
            print(f"  {item}")
        return

    if existing_ids:
        client.unlink("website.menu", existing_ids)
        print(f"Deleted {len(existing_ids)} existing items.")

    created_ids = {}
    for item in DESIRED_ITEMS:
        new_id = client.create("website.menu", {
            "name": item["name"],
            "url": item["url"],
            "sequence": item["sequence"],
            "parent_id": top_menu_id,
            "website_id": website_id,
        })
        created_ids[item["name"]] = new_id
        print(f"Created [{new_id}] {item['name']!r}")

    print("\nDone. New menu IDs:")
    print(json.dumps(created_ids, indent=2))


def set_mega(client, menu_id, html_file, dry_run=False):
    if not os.path.exists(html_file):
        sys.exit(f"ERROR: File not found: {html_file}")
    with open(html_file, "r", encoding="utf-8") as f:
        content = f.read().strip()

    if dry_run:
        print(f"[dry-run] Would set mega_menu_content on menu ID {menu_id}")
        print(f"[dry-run] Content length: {len(content)} chars")
        return

    client.write("website.menu", [menu_id], {"mega_menu_content": content})
    print(f"Set mega_menu_content on menu ID {menu_id} ({len(content)} chars).")


def main():
    parser = argparse.ArgumentParser(description="Manage website.menu for 19prince nav")
    group = parser.add_mutually_exclusive_group(required=True)
    group.add_argument("--list", action="store_true")
    group.add_argument("--restructure", action="store_true")
    group.add_argument("--set-mega", action="store_true")
    parser.add_argument("--menu-id", type=int, help="Menu item ID (for --set-mega)")
    parser.add_argument("--file", help="HTML file path (for --set-mega)")
    parser.add_argument("--dry-run", action="store_true")
    parser.add_argument("--prod", action="store_true", help="Target production instead of staging")
    parser.add_argument("--website-id", type=int, help="Override website ID")
    parser.add_argument("--top-menu-id", type=int, help="Override top menu parent ID")
    args = parser.parse_args()

    target = "PRODUCTION" if args.prod else "STAGING"
    client = get_client(prod=args.prod)
    client.authenticate()
    print(f"Target: {target} ({client.url})")

    website_id, top_menu_id = get_ids(
        client, prod=args.prod,
        website_id=args.website_id, top_menu_id=args.top_menu_id,
    )
    print(f"Website ID: {website_id}, Top Menu ID: {top_menu_id}")

    if args.list:
        list_items(client, top_menu_id)
    elif args.restructure:
        restructure(client, website_id, top_menu_id, dry_run=args.dry_run)
    elif args.set_mega:
        if not args.menu_id or not args.file:
            sys.exit("ERROR: --set-mega requires --menu-id and --file")
        set_mega(client, args.menu_id, args.file, dry_run=args.dry_run)


if __name__ == "__main__":
    main()
