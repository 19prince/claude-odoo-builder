"""
Interactive CRM sync review server.

Reads a staging YAML file, serves a browser-based decision table, and pushes
approved items to Odoo when you click "Push to Odoo".

Usage:
    python3 tools/crm_review_server.py --staging "/path/to/YYYY-MM-DD-staging.yaml"
    # Opens http://localhost:8765 automatically. Press Ctrl-C to stop.
"""

import argparse
import datetime
import html
import json
import os
import sys
import webbrowser
from http.server import BaseHTTPRequestHandler, HTTPServer
from threading import Timer

import yaml

sys.path.insert(0, os.path.dirname(__file__))
from odoo_client import OdooClient

PORT = 8765


# ── Odoo helpers (mirrored from push_crm_updates.py) ─────────────────────────

def _get_or_create_crm_tag(client, name):
    existing = client.search("crm.tag", [("name", "=", name)], limit=1)
    if existing:
        return existing[0]
    return client.create("crm.tag", {"name": name})


def _get_stage_id(client, stage_name="New"):
    stages = client.search_read(
        "crm.stage",
        [("name", "ilike", stage_name)],
        ["id", "name"],
        limit=1,
    )
    return stages[0]["id"] if stages else None


def _create_lead(client, lead, extra_notes=""):
    name = lead.get("name", "Unknown — Email-Sync")
    email = lead.get("email", "")
    company = lead.get("company", "")
    notes = lead.get("notes", "")
    tags_str = lead.get("tags", "Email-Sync")

    if extra_notes:
        notes = notes.rstrip() + "\n\nReviewer notes: " + extra_notes

    tag_ids = []
    for tag_name in [t.strip() for t in tags_str.split(",") if t.strip()]:
        tag_ids.append(_get_or_create_crm_tag(client, tag_name))

    stage_id = _get_stage_id(client, "New")

    values = {"name": name, "type": "opportunity"}
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

    return client.create("crm.lead", values)


def markdown_bullets_to_html(text):
    """Convert markdown bullet list to <p> tags, newest-first (mirrors push_crm_updates.py)."""
    lines = reversed(text.strip().splitlines())
    items = []
    for line in lines:
        stripped = line.strip()
        if stripped.startswith("- "):
            items.append(f"<p>• {stripped[2:]}</p>")
        elif stripped:
            items.append(f"<p>{stripped}</p>")
    return "".join(items)


def _post_chatter_note(client, item, extra_notes=""):
    lead_id = item.get("lead_id")
    note = item.get("note", "")

    if extra_notes:
        note = note.rstrip() + "\n\nReviewer notes: " + extra_notes

    html_body = markdown_bullets_to_html(note)
    _post_direct_message(client, "crm.lead", lead_id, html_body)


def _find_or_create_partner(client, email, name=None, company=None):
    """Find res.partner by email, or create one if not found. Returns partner_id."""
    if not email:
        return None
    results = client.search_read(
        "res.partner", [("email", "=", email)], ["id", "name"], limit=1
    )
    if results:
        return results[0]["id"]
    vals = {"name": name or email, "email": email}
    if company:
        vals["company_name"] = company
    return client.create("res.partner", vals)


def _post_partner_note(client, partner_id, note, extra_notes=""):
    """Post a chatter note on a res.partner record."""
    if extra_notes:
        note = note.rstrip() + "\n\nReviewer notes: " + extra_notes
    html_body = markdown_bullets_to_html(note)
    _post_direct_message(client, "res.partner", partner_id, html_body)


def _resolve_partner_for_lead(client, lead_id):
    """Given a crm.lead id, return its linked partner_id or find/create by email_from."""
    records = client.read("crm.lead", [lead_id], ["partner_id", "email_from"])
    if not records:
        return None
    rec = records[0]
    if rec.get("partner_id"):
        return rec["partner_id"][0]  # (id, name) tuple → just id
    email = rec.get("email_from", "")
    if not email:
        return None
    return _find_or_create_partner(client, email)


def _post_direct_message(client, model, res_id, html_body, meeting_date=None):
    """Create mail.message directly — avoids HTML escaping that message_post causes.

    meeting_date is accepted for API compatibility but NOT used to set message.date.
    Odoo sorts chatter by create_date (set by ORM, cannot be overridden via API), so
    backdating via message.date only produces a misleading timestamp without placing the
    note in chronological order. The meeting date already appears in the body content.
    """
    subtypes = client.search_read(
        "mail.message.subtype", [("name", "=", "Note")], ["id"], limit=1
    )
    subtype_id = subtypes[0]["id"] if subtypes else 2
    users = client.search_read(
        "res.users", [("id", "=", client.uid)], ["partner_id"], limit=1
    )
    author_id = users[0]["partner_id"][0] if users else False
    values = {
        "body": html_body,
        "model": model,
        "res_id": res_id,
        "message_type": "comment",
        "subtype_id": subtype_id,
    }
    if author_id:
        values["author_id"] = author_id
    client.create("mail.message", values)


def _apply_state_change(client, item, decision, extra_notes=""):
    """Apply one state-change decision to crm.lead and post an audit note.

    decision is 'stage:<Name>' or 'promote'. Returns True if a write happened,
    False if it was an idempotent no-op. Re-reads the record first so a re-push
    (or a move already done in Odoo) is a safe no-op.
    """
    record_id = item.get("record_id")
    if not record_id:
        raise RuntimeError(f"No record id for state change {item.get('record_name')!r}")

    recs = client.read("crm.lead", [record_id], ["stage_id", "type"])
    if not recs:
        raise RuntimeError(f"crm.lead #{record_id} not found")
    rec = recs[0]
    cur_stage = rec["stage_id"][1] if rec.get("stage_id") else ""
    cur_type = rec.get("type")

    today = datetime.date.today().isoformat()

    if decision == "promote":
        if cur_type == "opportunity":
            print(f"  SKIP (already opportunity): #{record_id}")
            return False
        vals = {"type": "opportunity"}
        if not rec.get("stage_id"):
            sid = _get_stage_id(client, "New")
            if sid:
                vals["stage_id"] = sid
        client.write("crm.lead", [record_id], vals)
        audit = f"Promoted lead&rarr;opportunity via CRM sync {today}"
    elif decision.startswith("stage:"):
        target_name = decision.split(":", 1)[1]
        if cur_stage.lower() == target_name.lower():
            print(f"  SKIP (already at {target_name}): #{record_id}")
            return False
        sid = _get_stage_id(client, target_name)
        if not sid:
            raise RuntimeError(f"Stage {target_name!r} not found in crm.stage")
        client.write("crm.lead", [record_id], {"stage_id": sid})
        audit = f"Stage {_h(cur_stage or '—')}&rarr;{_h(target_name)} via CRM sync {today}"
    else:
        raise RuntimeError(f"Unknown state_change decision {decision!r}")

    parts = [audit]
    if item.get("evidence"):
        parts.append(f'evidence: "{_h(item["evidence"])}"')
    if item.get("source"):
        parts.append(f"source: {_h(item['source'])}")
    if extra_notes:
        parts.append(f"reviewer: {_h(extra_notes)}")
    _post_direct_message(client, "crm.lead", record_id, " &mdash; ".join(parts))
    print(f"  State change on #{record_id}: {decision}")
    return True


def process_decisions(data, decisions, pushed_set, client=None):
    """Push approved decisions to Odoo. Skips items already in pushed_set."""
    new_leads = data.get("new_leads") or []
    chatter_notes = data.get("chatter_notes") or []
    transcript_notes = data.get("transcript_notes") or []
    state_changes = data.get("state_changes") or []
    leads_created = 0
    notes_posted = 0
    stages_changed = 0
    errors = []
    skipped = 0

    if client is None:
        try:
            client = OdooClient()
        except SystemExit as e:
            return {"leads_created": 0, "contacts_created": 0, "notes_posted": 0,
                    "stages_changed": 0, "errors": [str(e)]}

    contacts_created = 0

    for d in decisions:
        dtype = d.get("type")
        idx = d.get("index")
        decision = d.get("decision", "skip")
        extra_notes = d.get("notes", "") if decision not in ("skip",) else ""
        key = (dtype, idx)

        if decision == "skip":
            continue

        if key in pushed_set:
            skipped += 1
            print(f"  SKIP (already pushed): {dtype} index {idx}")
            continue

        try:
            if dtype == "new_lead" and isinstance(idx, int) and 0 <= idx < len(new_leads):
                lead = new_leads[idx]
                if decision in ("lead", "accept", "change"):
                    lead_id = _create_lead(client, lead, extra_notes)
                    pushed_set.add(key)
                    leads_created += 1
                    print(f"  Created lead #{lead_id}: {lead.get('name')!r}")
                elif decision == "contact":
                    email = lead.get("email", "")
                    if not email:
                        raise RuntimeError(f"Cannot create contact for {lead.get('name')!r}: no email")
                    pid = _find_or_create_partner(client, email, lead.get("name"), lead.get("company"))
                    if lead.get("notes") or extra_notes:
                        note = lead.get("notes", "")
                        _post_partner_note(client, pid, note, extra_notes)
                    pushed_set.add(key)
                    contacts_created += 1
                    print(f"  Created/found contact #{pid}: {lead.get('name')!r}")

            elif dtype == "chatter_note" and isinstance(idx, int) and 0 <= idx < len(chatter_notes):
                item = chatter_notes[idx]
                lead_id = item.get("lead_id")
                if decision in ("lead", "accept", "change"):
                    _post_chatter_note(client, item, extra_notes)
                    pushed_set.add(key)
                    notes_posted += 1
                    print(f"  Posted note on lead #{lead_id} ({item.get('lead_name')!r})")
                elif decision == "contact":
                    pid = _resolve_partner_for_lead(client, lead_id)
                    if not pid:
                        raise RuntimeError(f"Cannot find contact for lead #{lead_id}: no email or linked partner")
                    _post_partner_note(client, pid, item.get("note", ""), extra_notes)
                    pushed_set.add(key)
                    notes_posted += 1
                    print(f"  Posted note on contact #{pid} (lead #{lead_id})")
                elif decision == "both":
                    _post_chatter_note(client, item, extra_notes)
                    pid = _resolve_partner_for_lead(client, lead_id)
                    if not pid:
                        raise RuntimeError(f"Cannot find contact for lead #{lead_id}: no email or linked partner")
                    _post_partner_note(client, pid, item.get("note", ""), extra_notes)
                    pushed_set.add(key)
                    notes_posted += 2
                    print(f"  Posted note on lead #{lead_id} and contact #{pid}")

            elif dtype == "transcript_note" and isinstance(idx, int) and 0 <= idx < len(transcript_notes):
                item = transcript_notes[idx]
                target = item.get("suggested_target") or {}
                target_id = target.get("id")
                company = item.get("company", "")
                title = item.get("title", "Meeting")
                meeting_date = item.get("meeting_date", "")
                html_body = _build_transcript_html(item)

                if decision in ("lead", "opportunity"):
                    if not target_id:
                        raise RuntimeError(f"No target id for transcript {title!r}")
                    _post_direct_message(client, "crm.lead", target_id, html_body, meeting_date)
                    pushed_set.add(key)
                    notes_posted += 1
                    print(f"  Posted transcript on lead #{target_id} ({target.get('name')!r}): {title!r}")
                elif decision == "contact":
                    target_yaml_type = target.get("type", "")
                    if target_yaml_type in ("lead", "opportunity"):
                        # target_id is a crm.lead ID — resolve the linked partner
                        lead_data = client.search_read(
                            "crm.lead", [("id", "=", target_id)], ["partner_id"], limit=1
                        )
                        if not lead_data or not lead_data[0].get("partner_id"):
                            raise RuntimeError(
                                f"Lead/opp #{target_id} has no linked partner — cannot post to contact"
                            )
                        partner_id = lead_data[0]["partner_id"][0]
                    else:
                        if not target_id:
                            raise RuntimeError(f"No target id for transcript {title!r}")
                        partner_id = target_id
                    _post_direct_message(client, "res.partner", partner_id, html_body, meeting_date)
                    pushed_set.add(key)
                    notes_posted += 1
                    print(f"  Posted transcript on contact #{partner_id} ({target_yaml_type} #{target_id}): {title!r}")
                elif decision == "new_lead":
                    stage_id = _get_stage_id(client)
                    vals = {
                        "name": f"{company or title} — Transcript-{meeting_date}",
                        "type": "opportunity",
                    }
                    if company:
                        vals["partner_name"] = company
                    if stage_id:
                        vals["stage_id"] = stage_id
                    lead_id = client.create("crm.lead", vals)
                    _post_direct_message(client, "crm.lead", lead_id, html_body, meeting_date)
                    pushed_set.add(key)
                    leads_created += 1
                    notes_posted += 1
                    print(f"  Created lead #{lead_id} and posted transcript: {title!r}")

            elif dtype == "state_change" and isinstance(idx, int) and 0 <= idx < len(state_changes):
                item = state_changes[idx]
                if _apply_state_change(client, item, decision, extra_notes):
                    pushed_set.add(key)
                    stages_changed += 1

        except RuntimeError as e:
            errors.append(str(e))
            print(f"  ERROR: {e}")

    if skipped:
        print(f"  Skipped {skipped} already-pushed item(s).")

    return {"leads_created": leads_created, "contacts_created": contacts_created,
            "notes_posted": notes_posted, "stages_changed": stages_changed,
            "errors": errors}


# ── HTML rendering ────────────────────────────────────────────────────────────

def _h(text):
    """HTML-escape a value for safe insertion into HTML."""
    return html.escape(str(text or ""), quote=True)


def _truncate(text, n=250):
    text = (text or "").strip()
    return text[:n] + "…" if len(text) > n else text


def _dropdown(row_type, index):
    if row_type == "new_lead":
        options = (
            '<option value="skip" selected>— Skip</option>'
            '<option value="lead">Create as Lead</option>'
            '<option value="contact">Create as Contact</option>'
        )
    else:  # chatter_note
        options = (
            '<option value="skip" selected>— Skip</option>'
            '<option value="lead">Post to Lead</option>'
            '<option value="contact">Post to Contact</option>'
            '<option value="both">Post to Both</option>'
        )
    return (
        f'<select class="decision" data-type="{row_type}" data-index="{index}">'
        + options
        + "</select>"
    )


def _notes_field(row_type, index):
    return (
        f'<textarea class="reviewer-notes" data-type="{row_type}" '
        f'data-index="{index}" rows="2" placeholder="Notes…"></textarea>'
    )


def _transcript_dropdown(index, suggested_type=None, confidence=None, has_id=True):
    if not has_id:
        # No existing Odoo record — posting to lead/opportunity/contact would error.
        # Only allow creating a new lead or skipping.
        opts = [("skip", "— Skip"), ("new_lead", "Create New Lead")]
        options = "".join(
            f'<option value="{v}">{label}</option>' for v, label in opts
        )
    else:
        val_map = {"lead": "lead", "opportunity": "opportunity", "contact": "contact", "new_lead": "new_lead"}
        preselect = val_map.get(suggested_type, "skip") if confidence == "certain" else "skip"
        opts = [
            ("skip", "— Skip"),
            ("lead", "Post to Lead"),
            ("opportunity", "Post to Opportunity"),
            ("contact", "Post to Contact"),
            ("new_lead", "Create New Lead"),
        ]
        options = "".join(
            f'<option value="{v}"{" selected" if v == preselect else ""}>{label}</option>'
            for v, label in opts
        )
    return f'<select class="decision" data-type="transcript_note" data-index="{index}">{options}</select>'


# Move targets offered in the state-change dropdown (New is the start, rarely a
# target). Stage ids are resolved at push time via _get_stage_id (never hardcoded).
REACHABLE_STAGES = ["Qualified", "On Hold", "Won", "Lost"]


def _state_change_dropdown(index, change_type, suggested_stage, confidence, current_type):
    """Build the per-row dropdown for a state change.

    Pre-select the suggestion only when confidence == 'certain' AND the move is
    not Won/Lost (those are high-impact and always require an explicit pick).
    Promotion is offered only when the record is currently a lead.
    """
    stages = list(REACHABLE_STAGES)
    if suggested_stage and suggested_stage not in stages:
        stages.append(suggested_stage)

    opts = [("skip", "No change")]
    for s in stages:
        opts.append((f"stage:{s}", f"Move to {s}"))
    if current_type == "lead":
        opts.append(("promote", "Promote to Opportunity"))

    preselect = "skip"
    if confidence == "certain":
        if change_type == "stage" and suggested_stage and suggested_stage not in ("Won", "Lost"):
            preselect = f"stage:{suggested_stage}"
        elif change_type == "promote":
            preselect = "promote"

    options = "".join(
        f'<option value="{html.escape(v)}"{" selected" if v == preselect else ""}>{html.escape(label)}</option>'
        for v, label in opts
    )
    return f'<select class="decision" data-type="state_change" data-index="{index}">{options}</select>'


def _build_transcript_html(item):
    meeting_date = html.escape(str(item.get("meeting_date", "") or ""))
    summary = item.get("summary") or []
    obsidian_link = item.get("obsidian_link", "")
    parts = [f"<p><strong>Meeting — {meeting_date}</strong></p>"]
    for bullet in summary:
        bullet = (bullet or "").strip()
        if bullet:
            parts.append(f"<p>• {html.escape(bullet)}</p>")
    if obsidian_link:
        parts.append(f'<p><a href="{html.escape(obsidian_link)}">View transcript in Obsidian</a></p>')
    return "".join(parts)


def render_html(data):
    new_leads = data.get("new_leads") or []
    chatter_notes = data.get("chatter_notes") or []
    transcript_notes = data.get("transcript_notes") or []
    period_start = _h(data.get("period_start", "?"))
    period_end = _h(data.get("period_end", "?"))
    generated = _h(data.get("generated", "?"))

    # New leads table rows
    leads_rows = ""
    for i, lead in enumerate(new_leads):
        leads_rows += (
            "<tr>"
            f"<td><strong>{_h(lead.get('company', ''))}</strong></td>"
            f"<td>{_h(lead.get('email', ''))}</td>"
            f"<td class='preview'>{_h(_truncate(lead.get('notes', '')))}</td>"
            f"<td>{_dropdown('new_lead', i)}</td>"
            f"<td>{_notes_field('new_lead', i)}</td>"
            "</tr>"
        )

    leads_section = ""
    if new_leads:
        leads_section = f"""
<h2>New Leads to Create <span class="count">({len(new_leads)})</span></h2>
<table>
<thead><tr>
  <th style="width:16%">Company</th>
  <th style="width:19%">Email</th>
  <th>Notes</th>
  <th style="width:16%">Decision</th>
  <th style="width:17%">Your Notes</th>
</tr></thead>
<tbody>{leads_rows}</tbody>
</table>"""

    # Chatter notes table rows
    notes_rows = ""
    for i, item in enumerate(chatter_notes):
        lead_label = _h(item.get("lead_name", f"Lead #{item.get('lead_id')}"))
        lead_id_label = _h(item.get("lead_id", ""))
        notes_rows += (
            "<tr>"
            f"<td><strong>{lead_label}</strong><br><small>#{lead_id_label}</small></td>"
            f"<td class='preview'>{_h(_truncate(item.get('note', '')))}</td>"
            f"<td>{_dropdown('chatter_note', i)}</td>"
            f"<td>{_notes_field('chatter_note', i)}</td>"
            "</tr>"
        )

    notes_section = ""
    if chatter_notes:
        notes_section = f"""
<h2>Chatter Notes for Existing Leads <span class="count">({len(chatter_notes)})</span></h2>
<table>
<thead><tr>
  <th style="width:20%">Lead</th>
  <th>Note</th>
  <th style="width:16%">Decision</th>
  <th style="width:17%">Your Notes</th>
</tr></thead>
<tbody>{notes_rows}</tbody>
</table>"""

    # Transcript notes table rows
    transcript_rows = ""
    for i, item in enumerate(transcript_notes):
        title = _h(item.get("title", "Meeting"))
        meeting_date = _h(item.get("meeting_date", ""))
        company = _h(item.get("company", ""))
        obsidian_link = item.get("obsidian_link", "")
        summary = item.get("summary") or []
        target = item.get("suggested_target") or {}
        target_name = _h(target.get("name", ""))
        target_type = _h(target.get("type", ""))
        confidence = target.get("confidence", "uncertain")

        bullets_html = "".join(f"<li>{_h(b)}</li>" for b in summary if b)
        obs_link_html = (
            f'<a href="{_h(obsidian_link)}" class="vault-link">Open in Obsidian ↗</a>'
            if obsidian_link else ""
        )
        row_class = ' class="uncertain"' if confidence == "uncertain" else ""

        transcript_rows += (
            f"<tr{row_class}>"
            f"<td><strong>{title}</strong><br><small>{meeting_date}</small></td>"
            f"<td>{company}</td>"
            f"<td class='preview'><ul class='summary-bullets'>{bullets_html}</ul></td>"
            f"<td>{obs_link_html}<br><small class='target-hint'>{target_type}: {target_name}</small></td>"
            f"<td>{_transcript_dropdown(i, target.get('type'), confidence, has_id=bool(target.get('id')))}</td>"
            f"<td>{_notes_field('transcript_note', i)}</td>"
            "</tr>"
        )

    transcript_section = ""
    if transcript_notes:
        transcript_section = f"""
<h2>Meeting Transcripts <span class="count">({len(transcript_notes)})</span></h2>
<table>
<thead><tr>
  <th style="width:18%">Meeting</th>
  <th style="width:12%">Company</th>
  <th>Summary</th>
  <th style="width:14%">Obsidian</th>
  <th style="width:14%">Decision</th>
  <th style="width:14%">Your Notes</th>
</tr></thead>
<tbody>{transcript_rows}</tbody>
</table>"""

    # State-change rows
    state_changes = data.get("state_changes") or []
    state_rows = ""
    for i, item in enumerate(state_changes):
        record_name = _h(item.get("record_name", f"#{item.get('record_id')}"))
        record_id = _h(item.get("record_id", ""))
        current_stage = _h(item.get("current_stage", ""))
        evidence = _h(item.get("evidence", ""))
        source = _h(item.get("source", ""))
        confidence = item.get("confidence", "uncertain")
        change_type = item.get("change_type", "stage")
        suggested_stage = item.get("suggested_stage")
        current_type = item.get("current_type", "opportunity" if change_type == "stage" else "lead")
        row_class = ' class="uncertain"' if confidence == "uncertain" else ""
        dd = _state_change_dropdown(i, change_type, suggested_stage, confidence, current_type)
        state_rows += (
            f"<tr{row_class}>"
            f"<td><strong>{record_name}</strong><br><small>#{record_id}</small></td>"
            f"<td>{current_stage}</td>"
            f"<td class='preview'>{evidence}</td>"
            f"<td><small>{source}</small></td>"
            f"<td>{dd}</td>"
            f"<td>{_notes_field('state_change', i)}</td>"
            "</tr>"
        )

    state_section = ""
    if state_changes:
        state_section = f"""
<h2>Record State Changes <span class="count">({len(state_changes)})</span></h2>
<table>
<thead><tr>
  <th style="width:20%">Record</th>
  <th style="width:11%">Current Stage</th>
  <th>Evidence</th>
  <th style="width:14%">Source</th>
  <th style="width:15%">Decision</th>
  <th style="width:14%">Your Notes</th>
</tr></thead>
<tbody>{state_rows}</tbody>
</table>"""

    # Full page — CSS braces and JS braces must be doubled in f-string
    return f"""<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="utf-8">
<title>CRM Sync Review — {generated}</title>
<style>
* {{ box-sizing: border-box; margin: 0; padding: 0; }}
body {{ font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Helvetica, sans-serif;
       padding: 28px 36px 60px; background: #f5f6f8; color: #212529; font-size: 14px; }}
h1 {{ font-size: 1.35rem; font-weight: 700; margin-bottom: 4px; }}
.meta {{ color: #6c757d; font-size: 0.82rem; margin-bottom: 28px; }}
h2 {{ font-size: 1rem; font-weight: 600; margin: 32px 0 8px; color: #343a40; }}
.count {{ font-weight: 400; color: #6c757d; }}
table {{ width: 100%; border-collapse: collapse; background: #fff;
         border-radius: 7px; overflow: hidden;
         box-shadow: 0 1px 4px rgba(0,0,0,.09); margin-bottom: 6px; }}
th {{ background: #2d3748; color: #e2e8f0; padding: 9px 12px;
      text-align: left; font-size: 0.75rem; text-transform: uppercase;
      letter-spacing: .05em; font-weight: 600; }}
td {{ padding: 9px 12px; border-bottom: 1px solid #e9ecef;
      vertical-align: top; line-height: 1.45; }}
tr:last-child td {{ border-bottom: none; }}
tr:hover td {{ background: #f8f9fa; }}
td.preview {{ font-size: 0.81rem; color: #495057; white-space: pre-wrap; }}
small {{ color: #868e96; font-size: 0.78rem; }}
select.decision {{ width: 100%; padding: 5px 7px; border: 1px solid #ced4da;
                   border-radius: 4px; font-size: 0.83rem; background: #fff;
                   cursor: pointer; }}
select.decision:focus {{ outline: none; border-color: #4a90d9; }}
textarea.reviewer-notes {{ width: 100%; padding: 5px 7px; border: 1px solid #ced4da;
                            border-radius: 4px; font-size: 0.82rem; resize: vertical;
                            font-family: inherit; line-height: 1.4; }}
textarea.reviewer-notes:focus {{ outline: none; border-color: #4a90d9; }}
.action-bar {{ margin-top: 36px; display: flex; align-items: center; gap: 16px; flex-wrap: wrap; }}
#push-btn {{ background: #1a73e8; color: #fff; border: none; padding: 11px 26px;
             border-radius: 6px; font-size: 0.95rem; font-weight: 600;
             cursor: pointer; letter-spacing: .01em; }}
#push-btn:hover:not(:disabled) {{ background: #1558c0; }}
#push-btn:disabled {{ background: #868e96; cursor: not-allowed; }}
#result {{ padding: 10px 16px; border-radius: 6px; font-size: 0.88rem; display: none; }}
#result.success {{ background: #d4edda; border: 1px solid #b8dbc4; color: #155724; }}
#result.error {{ background: #f8d7da; border: 1px solid #f1b0b7; color: #721c24; }}
tr.uncertain td {{ background: #fff9e6; }}
tr.uncertain:hover td {{ background: #fff3cc; }}
a.vault-link {{ color: #7c5cbf; font-size: 0.82rem; text-decoration: none; }}
a.vault-link:hover {{ text-decoration: underline; }}
.target-hint {{ color: #868e96; }}
ul.summary-bullets {{ margin: 0; padding-left: 16px; font-size: 0.81rem; color: #495057; line-height: 1.5; }}
</style>
</head>
<body>

<h1>CRM Email Sync — Review &amp; Push</h1>
<div class="meta">Period: {period_start} → {period_end} &nbsp;·&nbsp; Generated: {generated}</div>

{leads_section}
{notes_section}
{transcript_section}
{state_section}

<div class="action-bar">
  <button id="push-btn" onclick="pushToOdoo()">Push to Odoo</button>
  <div id="result"></div>
</div>

<script>
function lockForm() {{
  document.querySelectorAll('select.decision, textarea.reviewer-notes').forEach(function(el) {{
    el.disabled = true;
  }});
  const btn = document.getElementById('push-btn');
  btn.disabled = true;
  btn.textContent = '✓ Pushed — reload page to push again';
  btn.style.background = '#28a745';
}}

function pushToOdoo() {{
  const decisions = [];
  document.querySelectorAll('select.decision').forEach(function(sel) {{
    const ta = document.querySelector(
      'textarea.reviewer-notes[data-type="' + sel.dataset.type + '"][data-index="' + sel.dataset.index + '"]'
    );
    decisions.push({{
      type: sel.dataset.type,
      index: parseInt(sel.dataset.index, 10),
      decision: sel.value,
      notes: ta ? ta.value.trim() : ''
    }});
  }});

  const active = decisions.filter(function(d) {{ return d.decision !== 'skip'; }});
  if (active.length === 0) {{
    alert('Nothing to push — all rows are set to Skip.\\nSelect an action on at least one row.');
    return;
  }}

  const btn = document.getElementById('push-btn');
  const result = document.getElementById('result');
  btn.disabled = true;
  btn.textContent = 'Pushing…';
  result.style.display = 'none';

  fetch('/push', {{
    method: 'POST',
    headers: {{'Content-Type': 'application/json'}},
    body: JSON.stringify({{decisions: decisions}})
  }})
  .then(function(r) {{ return r.json(); }})
  .then(function(data) {{
    result.style.display = 'block';
    if (data.errors && data.errors.length > 0) {{
      result.className = 'error';
      result.innerHTML = '<strong>Errors:</strong><br>' +
        data.errors.map(function(e) {{ return '• ' + e; }}).join('<br>');
      btn.textContent = 'Push to Odoo';
      btn.disabled = false;
    }} else {{
      result.className = 'success';
      const parts = [];
      if (data.leads_created) parts.push('Leads created: ' + data.leads_created);
      if (data.contacts_created) parts.push('Contacts created: ' + data.contacts_created);
      if (data.notes_posted) parts.push('Notes posted: ' + data.notes_posted);
      if (data.stages_changed) parts.push('Stages changed: ' + data.stages_changed);
      result.innerHTML = '✓ <strong>Done.</strong> &nbsp;' + (parts.join(' &nbsp;·&nbsp; ') || 'Nothing new pushed.');
      lockForm();
    }}
  }})
  .catch(function(err) {{
    result.style.display = 'block';
    result.className = 'error';
    result.textContent = 'Request failed: ' + err.message;
    btn.textContent = 'Push to Odoo';
    btn.disabled = false;
  }});
}}
</script>
</body>
</html>"""


# ── Durable push-state (sidecar) + audit receipt ─────────────────────────────
# We do NOT rewrite the staging YAML in place — it carries human comments that
# yaml.safe_dump would destroy. Instead push-state lives in a <staging>.pushed.json
# sidecar (so restarts don't re-push) and a human-readable markdown receipt.

def _sidecar_path(staging_path):
    return staging_path + ".pushed.json"


def _load_pushed(staging_path):
    """Seed the pushed-set from the sidecar so a restart won't re-push."""
    p = _sidecar_path(staging_path)
    if not os.path.exists(p):
        return set()
    try:
        with open(p) as f:
            rec = json.load(f)
        out = set()
        for k in rec.get("pushed", []):
            t, i = k.rsplit("|", 1)
            out.add((t, int(i)))
        return out
    except Exception as e:
        print(f"  WARN: could not read push sidecar: {e}")
        return set()


def _save_pushed(staging_path, pushed_set):
    rec = {
        "pushed": [f"{t}|{i}" for (t, i) in sorted(pushed_set, key=lambda x: (x[0], x[1]))],
        "updated_at": datetime.datetime.now().isoformat(timespec="seconds"),
    }
    with open(_sidecar_path(staging_path), "w") as f:
        json.dump(rec, f, indent=1)


def _label_for(data, dtype, idx):
    try:
        if dtype == "new_lead":
            return (data.get("new_leads") or [])[idx].get("name", "")
        if dtype == "chatter_note":
            item = (data.get("chatter_notes") or [])[idx]
            return item.get("lead_name") or f"lead #{item.get('lead_id')}"
        if dtype == "transcript_note":
            return (data.get("transcript_notes") or [])[idx].get("title", "")
        if dtype == "state_change":
            return (data.get("state_changes") or [])[idx].get("record_name", "")
    except (IndexError, AttributeError):
        pass
    return f"{dtype}[{idx}]"


def _write_receipt(staging_path, data, decisions, result, newly):
    """Append a human-readable push receipt next to the staging file."""
    receipt = os.path.join(os.path.dirname(staging_path), f"{datetime.date.today().isoformat()}-push-log.md")
    ts = datetime.datetime.now().isoformat(timespec="seconds")
    lines = [
        f"\n## Push {ts}",
        f"- staging: `{os.path.basename(staging_path)}`",
        f"- leads_created={result['leads_created']} contacts_created={result['contacts_created']} "
        f"notes_posted={result['notes_posted']} errors={len(result['errors'])}",
    ]
    pushed_any = False
    for d in decisions:
        key = (d.get("type"), d.get("index"))
        if key not in newly:
            continue
        pushed_any = True
        lines.append(f"  - PUSHED {key[0]} → {d.get('decision')} : {_label_for(data, key[0], key[1])}")
    if not pushed_any:
        lines.append("  - (nothing newly pushed)")
    for e in result["errors"]:
        lines.append(f"  - ERROR: {e}")
    with open(receipt, "a") as f:
        f.write("\n".join(lines) + "\n")
    return receipt


# ── HTTP server ───────────────────────────────────────────────────────────────

class ReviewHandler(BaseHTTPRequestHandler):
    staging_data = None
    staging_path = None
    _pushed = set()  # tracks (type, index) pairs already pushed (seeded from sidecar)

    def log_message(self, fmt, *args):
        pass  # suppress default access log

    def _load_data(self):
        """Re-read the staging file from disk so on-disk edits are reflected
        without restarting the server (fixes the stale in-memory page bug)."""
        try:
            with open(ReviewHandler.staging_path) as f:
                data = yaml.safe_load(f)
            if isinstance(data, dict):
                ReviewHandler.staging_data = data
        except Exception as e:
            print(f"  WARN: could not reload staging file: {e}")
        return ReviewHandler.staging_data

    def do_GET(self):
        if self.path != "/":
            self.send_response(404)
            self.end_headers()
            return
        body = render_html(self._load_data()).encode("utf-8")
        self.send_response(200)
        self.send_header("Content-Type", "text/html; charset=utf-8")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def do_POST(self):
        if self.path != "/push":
            self.send_response(404)
            self.end_headers()
            return

        length = int(self.headers.get("Content-Length", 0))
        raw = self.rfile.read(length)
        try:
            payload = json.loads(raw)
        except json.JSONDecodeError:
            self._send_json(400, {"error": "invalid JSON"})
            return

        print("\nProcessing decisions…")
        data = self._load_data()
        decisions = payload.get("decisions", [])
        before = set(ReviewHandler._pushed)
        result = process_decisions(data, decisions, ReviewHandler._pushed)
        newly = ReviewHandler._pushed - before
        if newly:
            _save_pushed(ReviewHandler.staging_path, ReviewHandler._pushed)
        receipt = _write_receipt(ReviewHandler.staging_path, data, decisions, result, newly)
        self._send_json(200, result)
        print(
            f"Done — leads created: {result['leads_created']}, "
            f"contacts created: {result['contacts_created']}, "
            f"notes posted: {result['notes_posted']}, "
            f"errors: {len(result['errors'])}  |  receipt: {os.path.basename(receipt)}"
        )

    def _send_json(self, status, data):
        body = json.dumps(data).encode("utf-8")
        self.send_response(status)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)


# ── Entry point ───────────────────────────────────────────────────────────────

def main():
    parser = argparse.ArgumentParser(description="Interactive CRM sync review server")
    parser.add_argument("--staging", required=True, help="Path to YYYY-MM-DD-staging.yaml")
    args = parser.parse_args()

    staging_path = os.path.expanduser(args.staging)
    if not os.path.exists(staging_path):
        sys.exit(f"ERROR: Staging file not found: {staging_path}")

    with open(staging_path) as f:
        data = yaml.safe_load(f)

    if not isinstance(data, dict):
        sys.exit("ERROR: Staging file is not a valid YAML mapping.")

    ReviewHandler.staging_data = data
    ReviewHandler.staging_path = staging_path
    ReviewHandler._pushed = _load_pushed(staging_path)

    new_leads = data.get("new_leads") or []
    chatter_notes = data.get("chatter_notes") or []
    transcript_notes = data.get("transcript_notes") or []

    server = HTTPServer(("localhost", PORT), ReviewHandler)
    url = f"http://localhost:{PORT}"

    print(f"\nCRM Review Server")
    print(f"  Staging file : {staging_path}  (re-read from disk on every request)")
    print(f"  New leads    : {len(new_leads)}")
    print(f"  Chatter notes: {len(chatter_notes)}")
    print(f"  Transcripts  : {len(transcript_notes)}")
    print(f"  Already pushed: {len(ReviewHandler._pushed)} item(s) (from sidecar — will be skipped)")
    print(f"  URL          : {url}")
    print(f"\nOpening browser… (Ctrl-C to stop)\n")

    Timer(0.6, webbrowser.open, args=[url]).start()

    try:
        server.serve_forever()
    except KeyboardInterrupt:
        print("\nServer stopped.")


if __name__ == "__main__":
    main()
