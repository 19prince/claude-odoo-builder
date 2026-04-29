"""
List Odoo email mailings and mailing lists.

Usage:
    python3 tools/list_mailings.py --mailings
    python3 tools/list_mailings.py --mailings --all
    python3 tools/list_mailings.py --lists
"""

import argparse
import json
import os
import sys

sys.path.insert(0, os.path.dirname(__file__))
from odoo_client import OdooClient


def list_mailings(client, show_all=False):
    limit = 0 if show_all else 10
    mailings = client.search_read(
        "mailing.mailing",
        [],
        ["id", "subject", "state", "sent_date", "create_date", "contact_list_ids"],
        limit=limit,
    )

    if not mailings:
        print("No mailings found. Create one in Odoo Email Marketing first.")
        return

    mailings.sort(key=lambda m: m["id"], reverse=True)

    col_id = max(4, max(len(str(m["id"])) for m in mailings))
    col_state = max(5, max(len(m["state"] or "") for m in mailings))
    col_subj = 50

    header = f"{'ID':<{col_id}}  {'State':<{col_state}}  {'Subject':<{col_subj}}  Date"
    print(header)
    print("-" * len(header))

    for m in mailings:
        date = m.get("sent_date") or m.get("create_date") or ""
        if date:
            date = str(date)[:10]
        subject = (m["subject"] or "")[:col_subj]
        print(
            f"{m['id']:<{col_id}}  "
            f"{m['state']:<{col_state}}  "
            f"{subject:<{col_subj}}  "
            f"{date}"
        )

    out_path = os.path.join(os.path.dirname(__file__), "..", ".tmp", "mailings_list.json")
    os.makedirs(os.path.dirname(out_path), exist_ok=True)
    with open(out_path, "w", encoding="utf-8") as f:
        json.dump(mailings, f, indent=2, default=str)
    print(f"\n{len(mailings)} mailing(s) listed. JSON saved to .tmp/mailings_list.json")


def list_mailing_lists(client):
    lists = client.search_read(
        "mailing.list",
        [],
        ["id", "name", "contact_count"],
    )

    if not lists:
        print("No mailing lists found. Create one in Odoo Email Marketing first.")
        return

    col_id = max(4, max(len(str(ml["id"])) for ml in lists))
    col_name = max(4, max(len(ml["name"] or "") for ml in lists))

    header = f"{'ID':<{col_id}}  {'Name':<{col_name}}  Contacts"
    print(header)
    print("-" * len(header))

    for ml in lists:
        print(
            f"{ml['id']:<{col_id}}  "
            f"{(ml['name'] or ''):<{col_name}}  "
            f"{ml.get('contact_count', 0)}"
        )

    print(f"\n{len(lists)} mailing list(s) found.")


def main():
    parser = argparse.ArgumentParser(description="List Odoo mailings and mailing lists")
    group = parser.add_mutually_exclusive_group(required=True)
    group.add_argument("--mailings", action="store_true", help="List email mailings")
    group.add_argument("--lists", action="store_true", help="List mailing lists")
    parser.add_argument("--all", action="store_true", help="Show all mailings (default: last 10)")
    args = parser.parse_args()

    client = OdooClient()

    if args.mailings:
        list_mailings(client, show_all=args.all)
    elif args.lists:
        list_mailing_lists(client)


if __name__ == "__main__":
    main()
