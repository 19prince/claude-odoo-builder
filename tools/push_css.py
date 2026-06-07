"""
Inject or replace a named CSS block in website.custom_code_head.
Idempotent: strips the previous block before appending the new one.

Usage:
    python3 tools/push_css.py --block-name shop --file .tmp/shop.css
    python3 tools/push_css.py --block-name shop --file .tmp/shop.css --dry-run
"""

import argparse
import os
import re
import sys

sys.path.insert(0, os.path.dirname(__file__))
from odoo_client import OdooClient


def main():
    parser = argparse.ArgumentParser(description="Inject a named CSS block into website.custom_code_head")
    parser.add_argument("--block-name", required=True, help="Name for the CSS block (e.g. 'shop')")
    parser.add_argument("--file", required=True, help="Path to CSS file (raw CSS, no <style> tags)")
    parser.add_argument("--dry-run", action="store_true", help="Print result without writing to Odoo")
    args = parser.parse_args()

    if not os.path.exists(args.file):
        sys.exit(f"ERROR: File not found: {args.file}")

    with open(args.file, "r", encoding="utf-8") as f:
        css_content = f.read().strip()

    client = OdooClient()

    sites = client.search_read("website", [], ["id", "custom_code_head"])
    if not sites:
        sys.exit("ERROR: No website record found.")

    site = sites[0]
    site_id = site["id"]
    original_head = site.get("custom_code_head") or ""

    # Strip old block (idempotent — no-op if block doesn't exist yet)
    marker_start = f"/* == {args.block_name} start == */"
    marker_end = f"/* == {args.block_name} end == */"
    pattern = re.escape(marker_start) + r".*?" + re.escape(marker_end)
    head = re.sub(pattern, "", original_head, flags=re.DOTALL).strip()

    # Build new block — markers must be inside <style> tags
    new_block = f"<style>\n{marker_start}\n{css_content}\n{marker_end}\n</style>"
    new_head = (head + "\n" + new_block).strip() if head else new_block

    char_delta = len(new_head) - len(original_head)

    if args.dry_run:
        print("--- DRY RUN: resulting custom_code_head ---")
        print(new_head)
        print(f"--- char delta: {char_delta:+d} ---")
        sys.exit(0)

    try:
        client.write("website", [site_id], {"custom_code_head": new_head})
    except RuntimeError as e:
        sys.exit(f"ERROR: {e}")

    print(f"OK: pushed block '{args.block_name}' to website ID {site_id}")
    print(f"    custom_code_head: {len(new_head)} chars total ({char_delta:+d} from previous)")


if __name__ == "__main__":
    main()
