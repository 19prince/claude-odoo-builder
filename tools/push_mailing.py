"""
Create or update an Odoo email mailing (always as draft — never sends).

Usage:
    # Create new draft mailing
    python3 tools/push_mailing.py --create \
      --subject "Your subject" --file .tmp/draft_mailing.html --list-id 1

    # Update existing mailing body
    python3 tools/push_mailing.py --update --id 18 --file .tmp/draft_mailing.html

    # Update subject only
    python3 tools/push_mailing.py --update --id 18 --subject "New subject"
"""

import argparse
import os
import sys

sys.path.insert(0, os.path.dirname(__file__))
from odoo_client import OdooClient


def get_mailing_model_id(client):
    """Find the ir.model ID for 'mailing.list' (used as mailing_model_id)."""
    models = client.search_read(
        "ir.model",
        [("model", "=", "mailing.list")],
        ["id"],
        limit=1,
    )
    if not models:
        sys.exit(
            "ERROR: Model 'mailing.list' not found. "
            "Is the Email Marketing module installed?"
        )
    return models[0]["id"]


def cmd_create(client, args, tmp_dir):
    if not args.subject:
        sys.exit("ERROR: --subject is required for --create")
    if not args.file:
        sys.exit("ERROR: --file is required for --create")

    mailing_model_id = get_mailing_model_id(client)

    values = {
        "subject": args.subject,
        "body_arch": args.content,
        "body_html": args.content,
        "mailing_type": "mail",
        "mailing_model_id": mailing_model_id,
    }

    if args.list_id:
        values["contact_list_ids"] = [(6, 0, [args.list_id])]

    mailing_id = client.create("mailing.mailing", values)

    print(f"Created mailing ID: {mailing_id}")
    print(f"Subject: {args.subject}")
    print(f"State: draft (will not send automatically)")
    if args.list_id:
        print(f"Mailing list ID: {args.list_id}")
    url = client.url
    print(f"\nView in Odoo: {url}/web#id={mailing_id}&model=mailing.mailing&view_type=form")


def cmd_update(client, args, tmp_dir):
    if not args.mailing_id:
        sys.exit("ERROR: --id is required for --update")
    if not args.file and not args.subject:
        sys.exit("ERROR: --update requires --file and/or --subject")

    records = client.read(
        "mailing.mailing",
        [args.mailing_id],
        ["id", "subject", "state", "body_arch"],
    )
    if not records:
        sys.exit(f"ERROR: No mailing found with ID {args.mailing_id}")

    mailing = records[0]

    if args.file and mailing.get("body_arch"):
        backup_path = os.path.join(tmp_dir, f"mailing_{args.mailing_id}_backup.html")
        with open(backup_path, "w", encoding="utf-8") as f:
            f.write(mailing["body_arch"])
        print(f"Backup saved: .tmp/mailing_{args.mailing_id}_backup.html")

    values = {}
    if args.file:
        values["body_arch"] = args.content
        values["body_html"] = args.content
    if args.subject:
        values["subject"] = args.subject

    client.write("mailing.mailing", [args.mailing_id], values)

    print(f"Updated mailing ID: {args.mailing_id}")
    if args.subject:
        print(f"Subject: {args.subject}")
    if args.file:
        print(f"Body updated from: {args.file}")
    url = client.url
    print(f"\nView in Odoo: {url}/web#id={args.mailing_id}&model=mailing.mailing&view_type=form")


def main():
    parser = argparse.ArgumentParser(description="Create or update an Odoo email mailing")

    mode = parser.add_mutually_exclusive_group(required=True)
    mode.add_argument("--create", action="store_true", help="Create a new draft mailing")
    mode.add_argument("--update", action="store_true", help="Update an existing mailing")

    parser.add_argument("--id", type=int, dest="mailing_id", help="Mailing ID (for --update)")
    parser.add_argument("--subject", help="Email subject line")
    parser.add_argument("--file", help="Path to HTML body_arch file")
    parser.add_argument("--list-id", type=int, dest="list_id", help="Mailing list ID to target")

    args = parser.parse_args()

    tmp_dir = os.path.join(os.path.dirname(__file__), "..", ".tmp")
    os.makedirs(tmp_dir, exist_ok=True)

    client = OdooClient()

    if args.file:
        if not os.path.exists(args.file):
            sys.exit(f"ERROR: File not found: {args.file}")
        with open(args.file, "r", encoding="utf-8") as f:
            args.content = f.read()
        if not args.content.strip():
            sys.exit(f"ERROR: File is empty: {args.file}")
    else:
        args.content = None

    if args.create:
        cmd_create(client, args, tmp_dir)
    elif args.update:
        cmd_update(client, args, tmp_dir)


if __name__ == "__main__":
    main()
