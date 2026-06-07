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


if __name__ == "__main__":
    unittest.main()
