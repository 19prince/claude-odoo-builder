"""
Push approved CRM updates from a crm-email-sync staging file to Odoo.

Usage:
    python3 tools/push_crm_updates.py --staging <path/to/YYYY-MM-DD-staging.yaml>
    python3 tools/push_crm_updates.py --staging <path> --dry-run

Only items with `approved: true` are processed. Everything else is skipped.
"""

import argparse
import datetime
import html as html_module
import os
import sys

import yaml

sys.path.insert(0, os.path.dirname(__file__))
from odoo_client import OdooClient


def get_or_create_crm_tag(client, name):
    existing = client.search("crm.tag", [("name", "=", name)], limit=1)
    if existing:
        return existing[0]
    return client.create("crm.tag", {"name": name})


def get_stage_id(client, stage_name="New"):
    stages = client.search_read(
        "crm.stage",
        [("name", "ilike", stage_name)],
        ["id", "name"],
        limit=1,
    )
    return stages[0]["id"] if stages else None


def push_new_lead(client, lead, dry_run):
    name = lead.get("name", "Unknown — Email-Sync")
    email = lead.get("email", "")
    company = lead.get("company", "")
    notes = lead.get("notes", "")
    tags_str = lead.get("tags", "Email-Sync")

    if dry_run:
        print(f"  [DRY RUN] Would create lead: {name!r} ({email})")
        return None

    tag_ids = []
    for tag_name in [t.strip() for t in tags_str.split(",") if t.strip()]:
        tag_ids.append(get_or_create_crm_tag(client, tag_name))

    stage_id = get_stage_id(client, "New")

    values = {
        "name": name,
        "type": "opportunity",
    }
    if email:
        values["email_from"] = email
    if company:
        values["partner_name"] = company
    if notes:
        values["description"] = notes
    if stage_id:
        values["stage_id"] = stage_id
    if tag_ids:
        values["tag_ids"] = [(6, 0, tag_ids)]

    lead_id = client.create("crm.lead", values)
    print(f"  Created lead #{lead_id}: {name!r}")
    return lead_id


def markdown_bullets_to_html(text):
    """Convert a markdown bullet list to <p> tags for Odoo's chatter."""
    lines = reversed(text.strip().splitlines())
    items = []
    for line in lines:
        stripped = line.strip()
        if stripped.startswith("- "):
            items.append(f"<p>• {stripped[2:]}</p>")
        elif stripped:
            items.append(f"<p>{stripped}</p>")
    return "".join(items)


def push_chatter_note(client, item, dry_run, base_url=""):
    original_lead_id = item.get("lead_id")
    original_lead_name = item.get("lead_name", f"Lead #{original_lead_id}")
    lead_id = item.get("redirect_lead_id") or original_lead_id
    lead_name = original_lead_name
    if item.get("redirect_lead_id"):
        lead_name = f"Lead #{lead_id} (redirected from #{original_lead_id})"
    note = item.get("note", "")

    if not lead_id:
        print(f"  SKIP: chatter note missing lead_id (lead: {lead_name!r})")
        return False

    if dry_run:
        print(f"  [DRY RUN] Would post note on lead #{lead_id} ({lead_name!r})")
        return True

    html = markdown_bullets_to_html(note)
    if item.get("redirect_lead_id") and base_url:
        html += (
            f'<p><em>Note redirected from: '
            f'<a href="{base_url}/odoo/crm/{original_lead_id}">{original_lead_name}</a>'
            f'</em></p>'
        )

    # message_post via RPC escapes HTML — create mail.message directly instead
    subtypes = client.search_read(
        "mail.message.subtype", [("name", "=", "Note")], ["id"], limit=1
    )
    subtype_id = subtypes[0]["id"] if subtypes else 2

    users = client.search_read(
        "res.users", [("id", "=", client.uid)], ["partner_id"], limit=1
    )
    author_id = users[0]["partner_id"][0] if users else False

    values = {
        "body": html,
        "model": "crm.lead",
        "res_id": lead_id,
        "message_type": "comment",
        "subtype_id": subtype_id,
    }
    if author_id:
        values["author_id"] = author_id

    client.create("mail.message", values)
    print(f"  Posted note on lead #{lead_id}: {lead_name!r}")
    return True


def transcript_summary_to_html(summary_bullets, meeting_date, obsidian_link):
    parts = [f"<p><strong>Meeting — {html_module.escape(meeting_date)}</strong></p>"]
    for bullet in summary_bullets:
        bullet = bullet.strip()
        if bullet:
            parts.append(f"<p>• {html_module.escape(bullet)}</p>")
    if obsidian_link:
        parts.append(f'<p><a href="{html_module.escape(obsidian_link)}">View transcript in Obsidian</a></p>')
    return "".join(parts)


def push_transcript_note(client, item, dry_run):
    title = item.get("title", "Meeting")
    meeting_date = item.get("meeting_date", "")
    company = item.get("company", "")
    obsidian_link = item.get("obsidian_link", "")
    summary = item.get("summary") or []
    target = item.get("suggested_target") or {}
    target_type = target.get("type", "lead")
    target_id = target.get("id")
    target_name = target.get("name", company)

    if dry_run:
        print(f"  [DRY RUN] Would post transcript: {title!r} → {target_type} #{target_id} ({target_name!r})")
        return True

    html_body = transcript_summary_to_html(summary, meeting_date, obsidian_link)

    subtypes = client.search_read(
        "mail.message.subtype", [("name", "=", "Note")], ["id"], limit=1
    )
    subtype_id = subtypes[0]["id"] if subtypes else 2

    users = client.search_read(
        "res.users", [("id", "=", client.uid)], ["partner_id"], limit=1
    )
    author_id = users[0]["partner_id"][0] if users else False

    def _create_message(model, res_id):
        values = {
            "body": html_body,
            "model": model,
            "res_id": res_id,
            "message_type": "comment",
            "subtype_id": subtype_id,
        }
        if author_id:
            values["author_id"] = author_id
        # meeting_date intentionally NOT set on message.date — Odoo sorts chatter by
        # create_date (ORM-controlled, not settable via API), so backdating only produces
        # a misleading timestamp without achieving chronological placement.
        client.create("mail.message", values)

    if target_type == "new_lead":
        stage_id = get_stage_id(client, "New")
        vals = {
            "name": f"{company or title} — Transcript-{meeting_date}",
            "type": "opportunity",
        }
        if company:
            vals["partner_name"] = company
        if stage_id:
            vals["stage_id"] = stage_id
        lead_id = client.create("crm.lead", vals)
        _create_message("crm.lead", lead_id)
        print(f"  Created lead #{lead_id} and posted transcript: {title!r}")
        return True

    if not target_id:
        print(f"  SKIP: transcript note missing target id (title: {title!r})")
        return False

    model = "crm.lead" if target_type in ("lead", "opportunity") else "res.partner"
    _create_message(model, target_id)
    print(f"  Posted transcript on {model} #{target_id} ({target_name!r}): {title!r}")
    return True


def _post_state_audit(client, record_id, body_html):
    subtypes = client.search_read(
        "mail.message.subtype", [("name", "=", "Note")], ["id"], limit=1
    )
    subtype_id = subtypes[0]["id"] if subtypes else 2
    users = client.search_read(
        "res.users", [("id", "=", client.uid)], ["partner_id"], limit=1
    )
    author_id = users[0]["partner_id"][0] if users else False
    vals = {"body": body_html, "model": "crm.lead", "res_id": record_id,
            "message_type": "comment", "subtype_id": subtype_id}
    if author_id:
        vals["author_id"] = author_id
    client.create("mail.message", vals)


def push_state_change(client, item, dry_run):
    """Apply a record state change (stage move or lead->opp promotion) and post
    an audit note. In this non-server path, `approved: true` IS the explicit
    pick, so Won/Lost are honored here (unlike the review-server pre-select)."""
    record_id = item.get("record_id")
    record_name = item.get("record_name", f"#{record_id}")
    change_type = item.get("change_type", "stage")
    suggested_stage = item.get("suggested_stage")

    if not record_id:
        print(f"  SKIP: state change missing record_id ({record_name!r})")
        return False

    if dry_run:
        tgt = "Promote to Opportunity" if change_type == "promote" else f"stage {suggested_stage}"
        print(f"  [DRY RUN] Would apply {tgt} on #{record_id} ({record_name!r})")
        return True

    recs = client.read("crm.lead", [record_id], ["stage_id", "type"])
    if not recs:
        print(f"  SKIP: crm.lead #{record_id} not found")
        return False
    rec = recs[0]
    cur_stage = rec["stage_id"][1] if rec.get("stage_id") else ""
    cur_type = rec.get("type")
    today = datetime.date.today().isoformat()
    e = html_module.escape

    if change_type == "promote":
        if cur_type == "opportunity":
            print(f"  SKIP (already opportunity): #{record_id}")
            return False
        vals = {"type": "opportunity"}
        if not rec.get("stage_id"):
            sid = get_stage_id(client, "New")
            if sid:
                vals["stage_id"] = sid
        client.write("crm.lead", [record_id], vals)
        audit = f"Promoted lead&rarr;opportunity via CRM sync {today}"
    else:
        if not suggested_stage:
            print(f"  SKIP: state change has no suggested_stage ({record_name!r})")
            return False
        if cur_stage.lower() == suggested_stage.lower():
            print(f"  SKIP (already at {suggested_stage}): #{record_id}")
            return False
        sid = get_stage_id(client, suggested_stage)
        if not sid:
            print(f"  SKIP: stage {suggested_stage!r} not found")
            return False
        client.write("crm.lead", [record_id], {"stage_id": sid})
        audit = f"Stage {e(cur_stage or '—')}&rarr;{e(suggested_stage)} via CRM sync {today}"

    parts = [audit]
    if item.get("evidence"):
        parts.append(f'evidence: "{e(item["evidence"])}"')
    if item.get("source"):
        parts.append(f"source: {e(item['source'])}")
    _post_state_audit(client, record_id, " &mdash; ".join(parts))
    print(f"  Applied state change on #{record_id} ({record_name!r})")
    return True


def main():
    parser = argparse.ArgumentParser(description="Push approved CRM sync updates to Odoo")
    parser.add_argument("--staging", required=True, help="Path to YYYY-MM-DD-staging.yaml")
    parser.add_argument("--dry-run", action="store_true", help="Preview without writing to Odoo")
    args = parser.parse_args()

    staging_path = os.path.expanduser(args.staging)
    if not os.path.exists(staging_path):
        sys.exit(f"ERROR: Staging file not found: {staging_path}")

    with open(staging_path) as f:
        data = yaml.safe_load(f)

    if not isinstance(data, dict):
        sys.exit("ERROR: Staging file is not a valid YAML mapping.")

    new_leads = data.get("new_leads") or []
    chatter_notes = data.get("chatter_notes") or []
    transcript_notes = data.get("transcript_notes") or []
    state_changes = data.get("state_changes") or []

    approved_leads = [l for l in new_leads if l.get("approved") is True]
    approved_notes = [n for n in chatter_notes if n.get("approved") is True]
    approved_transcripts = [t for t in transcript_notes if t.get("approved") is True]
    approved_states = [s for s in state_changes if s.get("approved") is True]

    if not approved_leads and not approved_notes and not approved_transcripts and not approved_states:
        print("Nothing approved. Set `approved: true` on items you want pushed, then re-run.")
        print(f"  Leads pending: {len(new_leads)} | Notes pending: {len(chatter_notes)} | "
              f"Transcripts pending: {len(transcript_notes)} | State changes pending: {len(state_changes)}")
        return

    mode = "DRY RUN — " if args.dry_run else ""
    print(f"\n{mode}CRM Sync Push")
    print(f"  Period: {data.get('period_start', '?')} → {data.get('period_end', '?')}")
    print(f"  Approved leads to create:  {len(approved_leads)}")
    print(f"  Approved notes to post:    {len(approved_notes)}")
    print(f"  Approved transcripts:      {len(approved_transcripts)}")
    print(f"  Approved state changes:    {len(approved_states)}")
    print()

    client = None if args.dry_run else OdooClient()
    base_url = (client.url if client else os.getenv("ODOO_URL", "")).rstrip("/")

    leads_created = 0
    notes_posted = 0
    transcripts_posted = 0
    states_changed = 0

    if approved_leads:
        print("New Leads:")
        for lead in approved_leads:
            result = push_new_lead(client, lead, args.dry_run)
            if result or args.dry_run:
                leads_created += 1

    if approved_notes:
        print("\nChatter Notes:")
        for item in approved_notes:
            result = push_chatter_note(client, item, args.dry_run, base_url)
            if result:
                notes_posted += 1

    if approved_transcripts:
        print("\nTranscript Notes:")
        for item in approved_transcripts:
            result = push_transcript_note(client, item, args.dry_run)
            if result:
                transcripts_posted += 1

    if approved_states:
        print("\nState Changes:")
        for item in approved_states:
            if push_state_change(client, item, args.dry_run):
                states_changed += 1

    print(f"\n{'[DRY RUN] ' if args.dry_run else ''}Done.")
    print(f"  Leads created:      {leads_created}")
    print(f"  Notes posted:       {notes_posted}")
    print(f"  Transcripts posted: {transcripts_posted}")
    print(f"  State changes:      {states_changed}")
    if (approved_leads + approved_notes + approved_transcripts + approved_states) and not args.dry_run:
        print(f"\nCheck Odoo CRM to verify the updates.")


if __name__ == "__main__":
    main()
