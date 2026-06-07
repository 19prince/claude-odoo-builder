"""
List all contact tags (res.partner.category) in Odoo.

Usage:
    python3 tools/list_partner_tags.py
"""

import os
import sys

sys.path.insert(0, os.path.dirname(__file__))
from odoo_client import OdooClient


def main():
    client = OdooClient()
    tags = client.search_read("res.partner.category", [], ["id", "name", "active"])

    if not tags:
        print("No contact tags found.")
        return

    tags.sort(key=lambda t: t["name"].lower())
    print(f"{'ID':<6}  Name")
    print("-" * 40)
    for t in tags:
        print(f"{t['id']:<6}  {t['name']}")
    print(f"\n{len(tags)} tag(s) found.")


if __name__ == "__main__":
    main()
