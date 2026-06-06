# Design — CRM Record State Changes (stage moves + lead→opp promotion)

Status: APPROVED design (Approach C). Not yet implemented. Build in a fresh session.
Author context: follows the 2026-06-06 CRM-sync retrospective (`~/.claude/plans/piped-swimming-wombat.md`).

## Context
The transcript/email CRM sync stages **notes** (new_leads / chatter_notes / transcript_notes) but never proposes **record state changes**. Darren wants the tool to suggest, from meeting/email signals: stage moves and lead→opportunity promotions — with **mandatory human review** before anything is written. This reuses the existing review-server (suggest → he approves/overrides → push) and the sidecar/receipt machinery added 2026-06-06.

## Decisions (locked)
- **Approach C:** a dedicated `state_changes` review panel, AND on apply, auto-post a one-line audit note to the record's chatter explaining the move + evidence.
- **Scope of moves:** advance forward (New→Qualified, Qualified→Won), Mark Lost, Park (On Hold); **Won only on explicit signed/closed signal**; plus **lead→opportunity promotion** (`type` flip).
- **Defaults:** pre-select the dropdown **only when confidence=certain**, EXCEPT **Won and Lost never pre-select** (always require an explicit pick) — they're high-impact. Everything else defaults to "No change".
- **Human-in-the-loop is non-negotiable:** nothing writes to Odoo without Darren picking it and clicking Push.

## Live pipeline (crm.stage)
New #1 → Qualified #2 → Won #4 (is_won) ; plus On Hold #3, Partner-Holding #7, Lost #5.
(Resolve ids at runtime via `crm.stage` search by name; don't hardcode if avoidable.)

## Data model — new staging section `state_changes`
Add a 4th top-level key to `YYYY-MM-DD-staging.yaml`:
```yaml
state_changes:
  - model: crm.lead            # always crm.lead for now
    record_id: 95
    record_name: "Website + Integration Proposal (Timberroot/Roasted Root)"
    current_stage: "Won"        # for display/sanity
    change_type: stage          # stage | promote
    suggested_stage: "Lost"     # for change_type=stage; omit for promote
    suggested_stage_id: 5       # resolved id (optional; resolve at push if absent)
    evidence: "went with DFW on the Roasted Root build out"   # quote from source
    source: "Gmail thread jessica@timberroot.com 2026-05-28"  # or obsidian link
    confidence: certain         # certain | uncertain
    approved: false
```
For a promotion: `change_type: promote`, omit suggested_stage; apply sets `type='opportunity'` and, if currently no real stage, `stage_id=New`.

## Detection (how the agent fills `state_changes`)
During inbox CRM sync (CLAUDE.md step 8) and email sync, after reading the **full** transcript/thread (per the 2026-06-06 rules), map explicit signals → suggested move. Only emit when there's a quotable signal; store the quote in `evidence`. Suggested mapping:
- "moving forward / approved / kicking off" → advance one stage (cap below Won).
- explicit "signed / closed / paid / we won" → Won (confidence certain only with hard proof).
- "went with <competitor> / not moving forward / dead" → Lost.
- "circle back / on hold / ghosted N weeks" → On Hold.
- a `type=lead` record showing real buying intent → promote.
Never infer Won from enthusiasm. If the current stage already equals the suggestion, emit nothing.

## Review UI (crm_review_server.py)
New panel "Record State Changes (n)" rendered like the others. Per row:
`record_name | current_stage → [dropdown] | evidence | source`.
Dropdown options: `No change` + each reachable stage + `Promote to Opportunity` (only when type=lead).
Pre-select rule: if `confidence==certain` AND suggested move ∉ {Won, Lost} → pre-select the suggestion; else default `No change`. Show the `evidence` quote inline so Darren can judge.

## Push / apply (process_decisions + push_crm_updates.py)
Add a `state_change` decision type. On approve:
1. Resolve target stage id (or `type='opportunity'` + stage New for promote).
2. `OdooClient.write('crm.lead', [record_id], {...})`.  ⚠️ **Prerequisite: confirm `OdooClient` has a `write()` wrapper; if not, add one** (xmlrpc `execute_kw(..., 'write', [[id], vals])`).
3. Post a one-line audit note via the existing `_post_direct_message(client,'crm.lead',id, html)`:
   `Stage Qualified→Won via CRM sync YYYY-MM-DD — evidence: "<quote>" — source: <source>`.
4. Record `(state_change, idx)` in the sidecar `_pushed` set; include in the markdown receipt (extend `_label_for` to handle `state_change`).
Idempotency: skip if `current_stage` already equals target at push time (re-read the lead's stage before writing).

## Files to modify
- `Vault DEO/CLAUDE.md` — step 8: add `state_changes` detection + signal→stage mapping; default approved:false.
- `19prince/tools/crm_review_server.py` — render panel (`render_html`), dropdown builder, `process_decisions` `state_change` branch, `_label_for`, pre-select rule.
- `19prince/tools/push_crm_updates.py` — mirror the `state_change` apply path for the non-server push.
- `19prince/tools/odoo_client.py` — ensure `write()` exists.

## Verification
- Dry-run: a staging file with one `state_change` (e.g., #95→Lost, certain) renders a panel; Won/Lost NOT pre-selected; forward move pre-selected.
- Apply against a throwaway/test lead: confirm `stage_id` changed AND an audit note posted; receipt + sidecar updated; re-push is a no-op.
- Confirm `OdooClient.write` round-trips.

## Out of scope (YAGNI)
Auto-applying moves; bulk reprocessing historical opps; lost_reason_id capture; multi-model (only crm.lead).

## Next-session prompt
```
Implement the CRM state-changes feature per docs/specs/2026-06-06-crm-state-changes-design.md
(Approach C). Start by invoking the writing-plans skill to turn this spec into an
implementation plan, then execute. First verify OdooClient.write exists (add if missing).
Do NOT auto-apply anything — all moves stay approved:false and require review-server pick.
Test the apply path on a throwaway lead, not a live opp.
```
