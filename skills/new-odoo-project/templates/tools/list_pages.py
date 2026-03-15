"""
List all Odoo website pages.

Usage:
    python3 tools/list_pages.py
    python3 tools/list_pages.py --url /about
    python3 tools/list_pages.py --published-only
"""

import argparse
import json
import os
import sys

sys.path.insert(0, os.path.dirname(__file__))
from odoo_client import OdooClient


def main():
    parser = argparse.ArgumentParser(description="List Odoo website pages")
    parser.add_argument("--url", help="Filter by exact URL (e.g. /about)")
    parser.add_argument(
        "--published-only", action="store_true", help="Only show published pages"
    )
    args = parser.parse_args()

    client = OdooClient()

    domain = [("active", "=", True)]
    if args.url:
        domain.append(("url", "=", args.url))
    if args.published_only:
        domain.append(("website_published", "=", True))

    pages = client.search_read(
        "website.page",
        domain,
        ["id", "name", "url", "view_id", "website_published", "is_homepage"],
    )

    if not pages:
        print("No pages found.")
        return

    # Print table
    col_id = max(len("ID"), max(len(str(p["id"])) for p in pages))
    col_pub = 9  # "Published"
    col_home = 8  # "Homepage"
    col_url = max(len("URL"), max(len(p["url"] or "") for p in pages))
    col_name = max(len("Name"), max(len(p["name"] or "") for p in pages))

    header = (
        f"{'ID':<{col_id}}  {'Published':<{col_pub}}  {'Homepage':<{col_home}}  "
        f"{'URL':<{col_url}}  {'Name':<{col_name}}  View ID"
    )
    print(header)
    print("-" * len(header))

    for p in pages:
        view_id = p["view_id"][0] if isinstance(p["view_id"], (list, tuple)) else p["view_id"]
        print(
            f"{p['id']:<{col_id}}  "
            f"{'Yes' if p['website_published'] else 'No':<{col_pub}}  "
            f"{'Yes' if p['is_homepage'] else 'No':<{col_home}}  "
            f"{(p['url'] or ''):<{col_url}}  "
            f"{(p['name'] or ''):<{col_name}}  "
            f"{view_id}"
        )

    # Save JSON for downstream tools
    out_path = os.path.join(os.path.dirname(__file__), "..", ".tmp", "pages_list.json")
    os.makedirs(os.path.dirname(out_path), exist_ok=True)
    with open(out_path, "w") as f:
        json.dump(pages, f, indent=2)
    print(f"\n{len(pages)} page(s) listed. Raw JSON saved to .tmp/pages_list.json")


if __name__ == "__main__":
    main()
