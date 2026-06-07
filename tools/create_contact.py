"""
Create an Odoo contact (res.partner).

Usage:
    python3 tools/create_contact.py --name "John Smith" --email "john@acme.com"
    python3 tools/create_contact.py --name "Acme Corp" --email "info@acme.com" \
        --company "Acme Corp" --tags "Newark-Roadshow-2026-05,Prospect" \
        --notes "Met at Newark show. Looking at inventory module." \
        --linkedin "https://linkedin.com/in/johnsmith" --phone "+1 555 123 4567"
"""

import argparse
import json
import os
import sys

sys.path.insert(0, os.path.dirname(__file__))
from odoo_client import OdooClient


def get_or_create_partner_tag(client, name):
    """Return ID of res.partner.category with this name, creating it if needed."""
    existing = client.search("res.partner.category", [("name", "=", name)], limit=1)
    if existing:
        return existing[0]
    return client.create("res.partner.category", {"name": name})


def main():
    parser = argparse.ArgumentParser(description="Create an Odoo contact")
    parser.add_argument("--name", required=True, help="Contact full name")
    parser.add_argument("--email", help="Email address")
    parser.add_argument("--phone", help="Phone number")
    parser.add_argument("--company", help="Company name (stored as company_name)")
    parser.add_argument(
        "--tags",
        help="Comma-separated tag names (e.g. 'Newark-Roadshow-2026-05,Prospect')",
    )
    parser.add_argument("--notes", help="Internal notes (comment field)")
    parser.add_argument("--linkedin", help="LinkedIn profile URL (stored in website field)")
    args = parser.parse_args()

    client = OdooClient()

    # Resolve tags
    tag_ids = []
    if args.tags:
        for tag_name in [t.strip() for t in args.tags.split(",") if t.strip()]:
            tag_ids.append(get_or_create_partner_tag(client, tag_name))

    values = {
        "name": args.name,
        "type": "contact",
    }
    if args.email:
        values["email"] = args.email
    if args.phone:
        values["phone"] = args.phone
    if args.company:
        values["company_name"] = args.company
    if args.notes:
        values["comment"] = args.notes
    if args.linkedin:
        values["website"] = args.linkedin
    if tag_ids:
        # many2many: [(6, 0, [ids])] replaces the full set
        values["category_id"] = [(6, 0, tag_ids)]

    contact_id = client.create("res.partner", values)

    result = {
        "id": contact_id,
        "name": args.name,
        "email": args.email or "",
        "company": args.company or "",
        "tags": args.tags or "",
        "linkedin": args.linkedin or "",
    }
    print(f"Contact created — ID: {contact_id}  Name: {args.name}")

    # Append to .tmp/created_contacts.json
    out_path = os.path.join(os.path.dirname(__file__), "..", ".tmp", "created_contacts.json")
    os.makedirs(os.path.dirname(out_path), exist_ok=True)
    existing = []
    if os.path.exists(out_path):
        with open(out_path) as f:
            try:
                existing = json.load(f)
            except json.JSONDecodeError:
                existing = []
    existing.append(result)
    with open(out_path, "w") as f:
        json.dump(existing, f, indent=2)

    return contact_id


if __name__ == "__main__":
    main()
