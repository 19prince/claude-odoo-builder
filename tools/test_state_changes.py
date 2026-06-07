"""Unit tests for CRM state-changes. Stdlib unittest, no network.

Run: python3 tools/test_state_changes.py
"""
import os
import sys
import unittest

sys.path.insert(0, os.path.dirname(__file__))
import crm_review_server as srv  # noqa: E402


class FakeClient:
    """Minimal stand-in for OdooClient. Records writes and messages."""

    def __init__(self, lead):
        # lead: dict with id, stage_id (tuple or False), type
        self.lead = dict(lead)
        self.uid = 1
        self.writes = []     # list of (model, ids, vals)
        self.messages = []   # list of mail.message create vals

    def read(self, model, ids, fields=None):
        if model == "crm.lead" and ids and ids[0] == self.lead["id"]:
            return [dict(self.lead)]
        return []

    def search_read(self, model, domain=None, fields=None, limit=0, offset=0):
        if model == "crm.stage":
            # domain like [("name","ilike", NAME)]
            name = domain[0][2]
            ids = {"New": 1, "Qualified": 2, "On Hold": 3, "Won": 4, "Lost": 5}
            sid = ids.get(name)
            return [{"id": sid, "name": name}] if sid else []
        if model == "mail.message.subtype":
            return [{"id": 2}]
        if model == "res.users":
            return [{"partner_id": [7, "Darren"]}]
        return []

    def write(self, model, ids, vals):
        self.writes.append((model, ids, vals))
        # reflect change so idempotency re-reads see it
        if model == "crm.lead" and ids[0] == self.lead["id"]:
            if "stage_id" in vals:
                self.lead["stage_id"] = [vals["stage_id"], "?"]
            if "type" in vals:
                self.lead["type"] = vals["type"]
        return True

    def create(self, model, vals):
        if model == "mail.message":
            self.messages.append(vals)
            return 999
        return 1


class TestImports(unittest.TestCase):
    def test_module_has_state_change_symbols(self):
        # These are added in later tasks; this test documents the contract.
        self.assertTrue(hasattr(srv, "REACHABLE_STAGES"))
        self.assertTrue(hasattr(srv, "_state_change_dropdown"))
        self.assertTrue(hasattr(srv, "_apply_state_change"))


class TestDropdown(unittest.TestCase):
    def test_forward_move_preselected_when_certain(self):
        html = srv._state_change_dropdown(
            0, change_type="stage", suggested_stage="Qualified",
            confidence="certain", current_type="opportunity")
        self.assertIn('value="stage:Qualified" selected', html)

    def test_won_never_preselected_even_when_certain(self):
        html = srv._state_change_dropdown(
            1, change_type="stage", suggested_stage="Won",
            confidence="certain", current_type="opportunity")
        self.assertIn('value="skip" selected', html)
        self.assertNotIn('value="stage:Won" selected', html)
        self.assertIn('value="stage:Won"', html)  # option still present

    def test_lost_never_preselected_even_when_certain(self):
        html = srv._state_change_dropdown(
            2, change_type="stage", suggested_stage="Lost",
            confidence="certain", current_type="opportunity")
        self.assertIn('value="skip" selected', html)
        self.assertNotIn('value="stage:Lost" selected', html)

    def test_uncertain_defaults_to_no_change(self):
        html = srv._state_change_dropdown(
            3, change_type="stage", suggested_stage="Qualified",
            confidence="uncertain", current_type="opportunity")
        self.assertIn('value="skip" selected', html)

    def test_promote_option_only_for_leads(self):
        as_lead = srv._state_change_dropdown(
            4, change_type="promote", suggested_stage=None,
            confidence="certain", current_type="lead")
        self.assertIn('value="promote" selected', as_lead)
        as_opp = srv._state_change_dropdown(
            5, change_type="stage", suggested_stage="Qualified",
            confidence="uncertain", current_type="opportunity")
        self.assertNotIn('value="promote"', as_opp)

    def test_suggested_stage_always_in_options(self):
        # even an off-list stage name must appear so preselect can target it
        html = srv._state_change_dropdown(
            6, change_type="stage", suggested_stage="Partner-Holding",
            confidence="uncertain", current_type="opportunity")
        self.assertIn('value="stage:Partner-Holding"', html)


class TestApply(unittest.TestCase):
    def _item(self, **kw):
        base = dict(model="crm.lead", record_id=95,
                    record_name="Timberroot opp", current_stage="Qualified",
                    change_type="stage", suggested_stage="Won",
                    evidence="they signed the SOW", source="Gmail 2026-05-28")
        base.update(kw)
        return base

    def test_stage_move_writes_and_posts_audit(self):
        c = FakeClient({"id": 95, "stage_id": [2, "Qualified"], "type": "opportunity"})
        applied = srv._apply_state_change(c, self._item(), "stage:Won")
        self.assertTrue(applied)
        self.assertEqual(c.writes, [("crm.lead", [95], {"stage_id": 4})])
        self.assertEqual(len(c.messages), 1)
        body = c.messages[0]["body"]
        self.assertIn("Qualified", body)
        self.assertIn("Won", body)
        self.assertIn("they signed the SOW", body)

    def test_idempotent_noop_when_already_at_target(self):
        c = FakeClient({"id": 95, "stage_id": [4, "Won"], "type": "opportunity"})
        applied = srv._apply_state_change(c, self._item(), "stage:Won")
        self.assertFalse(applied)
        self.assertEqual(c.writes, [])
        self.assertEqual(c.messages, [])

    def test_promote_flips_type_and_posts_audit(self):
        c = FakeClient({"id": 70, "stage_id": False, "type": "lead"})
        item = self._item(record_id=70, change_type="promote", suggested_stage=None)
        applied = srv._apply_state_change(c, item, "promote")
        self.assertTrue(applied)
        # type flip + stage New because it had no real stage
        self.assertEqual(c.writes[0][0], "crm.lead")
        vals = c.writes[0][2]
        self.assertEqual(vals["type"], "opportunity")
        self.assertEqual(vals["stage_id"], 1)
        self.assertIn("lead", c.messages[0]["body"].lower())

    def test_promote_noop_when_already_opportunity(self):
        c = FakeClient({"id": 70, "stage_id": [2, "Qualified"], "type": "opportunity"})
        item = self._item(record_id=70, change_type="promote", suggested_stage=None)
        applied = srv._apply_state_change(c, item, "promote")
        self.assertFalse(applied)
        self.assertEqual(c.writes, [])

    def test_process_decisions_routes_state_change(self):
        c = FakeClient({"id": 95, "stage_id": [2, "Qualified"], "type": "opportunity"})
        data = {"state_changes": [self._item()]}
        decisions = [{"type": "state_change", "index": 0, "decision": "stage:Won", "notes": ""}]
        pushed = set()
        result = srv.process_decisions(data, decisions, pushed, client=c)
        self.assertEqual(result["stages_changed"], 1)
        self.assertIn(("state_change", 0), pushed)


class TestRender(unittest.TestCase):
    def test_state_changes_section_renders(self):
        data = {
            "period_start": "2026-04-01", "period_end": "2026-06-06",
            "generated": "2026-06-06",
            "state_changes": [{
                "model": "crm.lead", "record_id": 95,
                "record_name": "Timberroot opp", "current_stage": "Qualified",
                "change_type": "stage", "suggested_stage": "Won",
                "evidence": "they signed", "source": "Gmail",
                "confidence": "certain", "approved": False,
            }],
        }
        html = srv.render_html(data)
        self.assertIn("Record State Changes", html)
        self.assertIn("Timberroot opp", html)
        self.assertIn("they signed", html)
        # Won is certain -> must NOT be pre-selected
        self.assertIn('value="skip" selected', html)
        self.assertNotIn('value="stage:Won" selected', html)

    def test_label_for_state_change(self):
        data = {"state_changes": [{"record_name": "Timberroot opp"}]}
        self.assertEqual(srv._label_for(data, "state_change", 0), "Timberroot opp")


if __name__ == "__main__":
    unittest.main()
