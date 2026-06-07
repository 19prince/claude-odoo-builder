"""
List all CRM lead/opportunity tags (crm.tag) in Odoo.

Usage:
    python3 tools/list_crm_tags.py
"""

import os
import sys

sys.path.insert(0, os.path.dirname(__file__))
from odoo_client import OdooClient


def main():
    client = OdooClient()
    tags = client.search_read("crm.tag", [], ["id", "name"])

    if not tags:
        print("No CRM tags found.")
        return

    tags.sort(key=lambda t: t["name"].lower())
    print(f"{'ID':<6}  Name")
    print("-" * 40)
    for t in tags:
        print(f"{t['id']:<6}  {t['name']}")
    print(f"\n{len(tags)} tag(s) found.")


if __name__ == "__main__":
    main()
