"""
Fetch the body_arch of an Odoo email mailing and save it locally.

Usage:
    python3 tools/get_mailing.py --id 15
    python3 tools/get_mailing.py --id 15 --no-backup
"""

import argparse
import os
import re
import sys

sys.path.insert(0, os.path.dirname(__file__))
from odoo_client import OdooClient


def main():
    parser = argparse.ArgumentParser(description="Fetch an Odoo mailing's body_arch")
    parser.add_argument("--id", type=int, required=True, dest="mailing_id", help="Mailing record ID")
    parser.add_argument("--no-backup", action="store_true", help="Skip saving backup file")
    args = parser.parse_args()

    client = OdooClient()

    records = client.read(
        "mailing.mailing",
        [args.mailing_id],
        ["id", "subject", "state", "body_arch", "contact_list_ids"],
    )

    if not records:
        sys.exit(f"ERROR: No mailing found with ID {args.mailing_id}")

    mailing = records[0]
    body_arch = mailing.get("body_arch") or ""

    if not body_arch:
        sys.exit(f"ERROR: Mailing {args.mailing_id} has no body_arch content.")

    section_count = len(re.findall(r'data-snippet=["\']s_title["\']', body_arch))

    tmp_dir = os.path.join(os.path.dirname(__file__), "..", ".tmp")
    os.makedirs(tmp_dir, exist_ok=True)

    if not args.no_backup:
        out_path = os.path.join(tmp_dir, f"mailing_{args.mailing_id}_body_arch.html")
        with open(out_path, "w", encoding="utf-8") as f:
            f.write(body_arch)
        print(f"Saved to: .tmp/mailing_{args.mailing_id}_body_arch.html")

    print(f"\n--- Mailing #{mailing['id']} ---")
    print(f"Subject: {mailing['subject']}")
    print(f"State:   {mailing['state']}")
    print(f"Lists:   {mailing['contact_list_ids']}")
    print(f"Sections (s_title count): {section_count}")
    print(f"Body arch length: {len(body_arch)} chars")


if __name__ == "__main__":
    main()
