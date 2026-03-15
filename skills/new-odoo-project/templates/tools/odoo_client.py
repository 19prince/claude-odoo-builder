"""
Odoo JSON-RPC client. Shared by all tools in this project.

Usage:
    from odoo_client import OdooClient
    client = OdooClient()        # reads from .env automatically
    pages = client.search_read("website.page", [], ["name", "url"])
"""

import json
import os
import sys

import requests
from dotenv import load_dotenv

load_dotenv(os.path.join(os.path.dirname(__file__), "..", ".env"))


class OdooClient:
    def __init__(self, url=None, db=None, user=None, password=None):
        self.url = (url or os.getenv("ODOO_URL", "")).rstrip("/")
        self.db = db or os.getenv("ODOO_DB", "")
        self.user = user or os.getenv("ODOO_USER", "")
        self.password = password or os.getenv("ODOO_PASSWORD", "")

        if not all([self.url, self.db, self.user, self.password]):
            sys.exit(
                "ERROR: Missing Odoo credentials. "
                "Set ODOO_URL, ODOO_DB, ODOO_USER, ODOO_PASSWORD in .env"
            )

        self.session = requests.Session()
        self.session.headers.update({"Content-Type": "application/json"})
        self.uid = None
        self._req_id = 0

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------

    def _next_id(self):
        self._req_id += 1
        return self._req_id

    def _post(self, endpoint, params):
        payload = {
            "jsonrpc": "2.0",
            "method": "call",
            "id": self._next_id(),
            "params": params,
        }
        try:
            resp = self.session.post(
                f"{self.url}{endpoint}",
                data=json.dumps(payload, ensure_ascii=False).encode("utf-8"),
                timeout=30,
            )
            resp.raise_for_status()
        except requests.RequestException as e:
            raise RuntimeError(f"HTTP error calling {endpoint}: {e}") from e

        body = resp.json()
        if "error" in body:
            err = body["error"]
            msg = err.get("data", {}).get("message") or err.get("message", str(err))
            raise RuntimeError(f"Odoo error: {msg}")
        return body["result"]

    def _execute_kw(self, model, method, args, kwargs=None):
        if self.uid is None:
            self.authenticate()
        return self._post(
            "/web/dataset/call_kw",
            {
                "model": model,
                "method": method,
                "args": args,
                "kwargs": kwargs or {},
            },
        )

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def authenticate(self):
        """Authenticate via /web/session/authenticate and store uid."""
        payload = {
            "jsonrpc": "2.0",
            "method": "call",
            "id": self._next_id(),
            "params": {
                "db": self.db,
                "login": self.user,
                "password": self.password,
            },
        }
        try:
            resp = self.session.post(
                f"{self.url}/web/session/authenticate",
                data=json.dumps(payload, ensure_ascii=False).encode("utf-8"),
                timeout=30,
            )
            resp.raise_for_status()
        except requests.RequestException as e:
            raise RuntimeError(f"HTTP error during authentication: {e}") from e

        body = resp.json()
        if "error" in body:
            err = body["error"]
            msg = err.get("data", {}).get("message") or err.get("message", str(err))
            raise RuntimeError(f"Authentication error: {msg}")

        result = body.get("result", {})
        uid = result.get("uid") if isinstance(result, dict) else None

        if not uid:
            raise RuntimeError(
                "Authentication failed — uid not returned. "
                "Check ODOO_USER and ODOO_PASSWORD."
            )
        self.uid = uid
        return self.uid

    def search_read(self, model, domain=None, fields=None, limit=0, offset=0):
        """Return list of dicts matching domain."""
        kwargs = {"fields": fields or [], "limit": limit, "offset": offset}
        return self._execute_kw(model, "search_read", [domain or []], kwargs)

    def read(self, model, ids, fields=None):
        """Read specific records by ID."""
        return self._execute_kw(model, "read", [ids], {"fields": fields or []})

    def search(self, model, domain=None, limit=0):
        """Return list of matching record IDs."""
        return self._execute_kw(model, "search", [domain or []], {"limit": limit})

    def create(self, model, values):
        """Create a record. Returns new record ID."""
        return self._execute_kw(model, "create", [values])

    def write(self, model, ids, values):
        """Update records. Returns True on success."""
        return self._execute_kw(model, "write", [ids, values])

    def unlink(self, model, ids):
        """Delete records. Returns True on success."""
        return self._execute_kw(model, "unlink", [ids])
