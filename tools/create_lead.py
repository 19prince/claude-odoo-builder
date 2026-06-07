"""
Create an Odoo CRM lead/opportunity (crm.lead).

Usage:
    python3 tools/create_lead.py --name "Acme Corp — Newark-Roadshow-2026-05" \
        --contact-id 42 --email "john@acme.com" \
        --tags "Newark-Roadshow-2026-05,Prospect,Warm" \
        --notes "Looking at inventory module. Self-implementing currently."
"""

import argparse
import json
import os
import sys

sys.path.insert(0, os.path.dirname(__file__))
from odoo_client import OdooClient


def get_or_create_crm_tag(client, name):
    """Return ID of crm.tag with this name, creating it if needed."""
    existing = client.search("crm.tag", [("name", "=", name)], limit=1)
    if existing:
        return existing[0]
    return client.create("crm.tag", {"name": name})


def get_stage_id(client, stage_name):
    """Return ID of the CRM stage matching stage_name, or None if not found."""
    stages = client.search_read(
        "crm.stage",
        [("name", "ilike", stage_name)],
        ["id", "name"],
        limit=1,
    )
    return stages[0]["id"] if stages else None


def main():
    parser = argparse.ArgumentParser(description="Create an Odoo CRM lead/opportunity")
    parser.add_argument("--name", required=True, help="Opportunity name (e.g. 'Acme Corp — Newark-Roadshow-2026-05')")
    parser.add_argument("--contact-id", type=int, help="Odoo partner ID to link this lead to")
    parser.add_argument("--email", help="Contact email")
    parser.add_argument("--company", help="Company name")
    parser.add_argument(
        "--tags",
        help="Comma-separated tag names (e.g. 'Newark-Roadshow-2026-05,Prospect,Warm')",
    )
    parser.add_argument("--notes", help="Lead description / internal notes")
    parser.add_argument("--stage", default="New", help="Pipeline stage name (default: New)")
    args = parser.parse_args()

    client = OdooClient()

    # Resolve tags
    tag_ids = []
    if args.tags:
        for tag_name in [t.strip() for t in args.tags.split(",") if t.strip()]:
            tag_ids.append(get_or_create_crm_tag(client, tag_name))

    # Resolve stage
    stage_id = get_stage_id(client, args.stage)

    values = {
        "name": args.name,
        "type": "lead",
    }
    if args.contact_id:
        values["partner_id"] = args.contact_id
    if args.email:
        values["email_from"] = args.email
    if args.company:
        values["partner_name"] = args.company
    if args.notes:
        values["description"] = args.notes
    if stage_id:
        values["stage_id"] = stage_id
    if tag_ids:
        values["tag_ids"] = [(6, 0, tag_ids)]

    lead_id = client.create("crm.lead", values)

    result = {
        "id": lead_id,
        "name": args.name,
        "contact_id": args.contact_id or "",
        "email": args.email or "",
        "company": args.company or "",
        "tags": args.tags or "",
        "stage": args.stage,
    }
    print(f"Lead created — ID: {lead_id}  Name: {args.name}")

    # Append to .tmp/created_leads.json
    out_path = os.path.join(os.path.dirname(__file__), "..", ".tmp", "created_leads.json")
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

    return lead_id


if __name__ == "__main__":
    main()
