"""
Push all CSS blocks from staging .tmp/ files to production.

Usage:
    python3 tools/push_css_to_prod.py
    python3 tools/push_css_to_prod.py --dry-run

Requires PROD_ODOO_URL, PROD_ODOO_DB, PROD_ODOO_USER, PROD_ODOO_PASSWORD in .env.
"""

import argparse
import os
import re
import sys

from dotenv import load_dotenv

load_dotenv(os.path.join(os.path.dirname(__file__), "..", ".env"))

sys.path.insert(0, os.path.dirname(__file__))
from odoo_client import OdooClient

TMP = os.path.join(os.path.dirname(__file__), "..", ".tmp")

# Ordered list of CSS blocks to push
BLOCKS = [
    ("header", "header.css"),
    ("shop",   "shop.css"),
    ("pages",  "pages.css"),
    ("forms",  "forms.css"),
    ("footer", "footer.css"),
]


def push_block(client, site_id, block_name, css_content, dry_run=False):
    sites = client.search_read("website", [], ["id", "custom_code_head"])
    site = next((s for s in sites if s["id"] == site_id), sites[0])
    original = site.get("custom_code_head") or ""

    marker_start = f"/* == {block_name} start == */"
    marker_end   = f"/* == {block_name} end == */"
    pattern = re.escape(marker_start) + r".*?" + re.escape(marker_end)
    head = re.sub(pattern, "", original, flags=re.DOTALL).strip()

    new_block = f"<style>\n{marker_start}\n{css_content}\n{marker_end}\n</style>"
    new_head = (head + "\n" + new_block).strip() if head else new_block

    delta = len(new_head) - len(original)

    if dry_run:
        print(f"  [DRY RUN] would push '{block_name}' ({delta:+d} chars)")
        return

    client.write("website", [site_id], {"custom_code_head": new_head})
    print(f"  OK  '{block_name}' pushed ({delta:+d} chars, total {len(new_head)})")


def main():
    parser = argparse.ArgumentParser(description="Push all CSS blocks to production")
    parser.add_argument("--dry-run", action="store_true")
    args = parser.parse_args()

    # Validate prod credentials
    # Normalize URL to scheme+host only (strip /odoo or other path prefixes)
    from urllib.parse import urlparse
    _raw_url = os.getenv("PROD_ODOO_URL", "").rstrip("/")
    _parsed  = urlparse(_raw_url)
    prod_url = f"{_parsed.scheme}://{_parsed.netloc}"
    prod_db   = os.getenv("PROD_ODOO_DB", "")
    prod_user = os.getenv("PROD_ODOO_USER", "")
    prod_pass = os.getenv("PROD_ODOO_PASSWORD", "")

    missing = [k for k, v in [
        ("PROD_ODOO_URL", prod_url), ("PROD_ODOO_DB", prod_db),
        ("PROD_ODOO_USER", prod_user), ("PROD_ODOO_PASSWORD", prod_pass)
    ] if not v]

    if missing:
        sys.exit(f"ERROR: Missing production credentials in .env: {', '.join(missing)}")

    print(f"Target: {prod_url}")
    if args.dry_run:
        print("Mode: DRY RUN\n")
    else:
        print("Mode: LIVE\n")

    client = OdooClient(url=prod_url, db=prod_db, user=prod_user, password=prod_pass)

    # Get production website ID
    sites = client.search_read("website", [], ["id", "name"])
    if not sites:
        sys.exit("ERROR: No website record found on production.")
    site_id = sites[0]["id"]
    print(f"Website: '{sites[0]['name']}' (ID {site_id})\n")

    # Push each block
    errors = []
    for block_name, filename in BLOCKS:
        filepath = os.path.join(TMP, filename)
        if not os.path.exists(filepath):
            print(f"  SKIP '{block_name}' — file not found: {filepath}")
            continue
        with open(filepath, "r", encoding="utf-8") as f:
            css_content = f.read().strip()
        try:
            push_block(client, site_id, block_name, css_content, dry_run=args.dry_run)
        except RuntimeError as e:
            print(f"  ERROR '{block_name}': {e}")
            errors.append(block_name)

    print()
    if errors:
        print(f"Finished with errors on: {', '.join(errors)}")
        sys.exit(1)
    else:
        action = "would be pushed" if args.dry_run else "pushed"
        print(f"All {len(BLOCKS)} blocks {action} successfully.")


if __name__ == "__main__":
    main()
