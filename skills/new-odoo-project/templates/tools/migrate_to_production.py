"""
Migrate staging changes to production.

Supports CSS theme views, page arches, and meta title/description updates.
Includes automatic backup and rollback capabilities.

Usage:
    # Preview — no changes made
    python3 tools/migrate_to_production.py --dry-run

    # Run migration (auto-backups current production state first)
    python3 tools/migrate_to_production.py

    # Rollback to a previous backup
    python3 tools/migrate_to_production.py --rollback .tmp/prod_backup_20260307_153000

Before running: update .env with PRODUCTION credentials.
"""

import argparse
import json
import os
import re
import sys
from datetime import datetime

sys.path.insert(0, os.path.dirname(__file__))
from odoo_client import OdooClient

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
TMP = os.path.join(BASE_DIR, ".tmp")

# ---------------------------------------------------------------------------
# Meta data gathered from staging (applied to pages by URL on production)
# ---------------------------------------------------------------------------
META_UPDATES = []

# View keys for CSS views we create/update — used during backup and rollback
CSS_VIEW_KEYS = []

# Page URLs whose arches we update
PAGE_URLS = []


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def log(msg, dry_run=False):
    prefix = "[DRY RUN] " if dry_run else ""
    print(f"{prefix}{msg}")


def find_view_by_key(client, key):
    """Return view record or None."""
    results = client.search_read(
        "ir.ui.view", [("key", "=", key)], ["id", "name", "arch"]
    )
    return results[0] if results else None


def strip_data_attrs(xml_content):
    """
    Strip inherit_id and name attributes from the outer <data> tag.
    Odoo stores inherit view arches as <data><xpath ...>...</xpath></data>
    without the module-level attributes.
    """
    cleaned = re.sub(
        r'<data\b[^>]*>',
        '<data>',
        xml_content.strip(),
        count=1,
    )
    return cleaned


def read_arch_from_xml(xml_file):
    """Read an XML theme file and return clean arch string."""
    with open(xml_file, "r", encoding="utf-8") as f:
        content = f.read()
    return strip_data_attrs(content)


def wrap_arch(content, url, name):
    """Wrap raw HTML in QWeb template wrapper."""
    if content.startswith("<t t-name="):
        return content
    url_slug = url.strip("/").replace("/", "_") or "home"
    key = f"website.page_{url_slug}"
    indented = "\n".join("    " + line for line in content.splitlines())
    safe_name = name.replace("'", "\\'")
    return (
        f'<t t-name="{key}">\n'
        f"  <t t-call=\"website.layout\">\n"
        f"    <t t-set=\"pageName\" t-value=\"'{safe_name}'\"/>\n"
        f"{indented}\n"
        f"  </t>\n"
        f"</t>"
    )


# ---------------------------------------------------------------------------
# Backup
# ---------------------------------------------------------------------------

def backup_state(client):
    """
    Snapshot current production state to .tmp/prod_backup_{timestamp}/.
    Returns the backup directory path.

    Saves:
      - manifest.json  — structured record of every view_id, page_id, and prior values
      - view_*.arch    — raw arch for each view being overwritten
      - meta.json      — current meta title/description for every page being updated
    """
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    backup_dir = os.path.join(TMP, f"prod_backup_{timestamp}")
    os.makedirs(backup_dir, exist_ok=True)

    manifest = {
        "timestamp": timestamp,
        "url": client.url,
        "db": client.db,
        "views": [],   # {action, view_id, key, arch_file} — action: "update" | "would_create"
        "pages": [],   # {view_id, url, arch_file}
        "meta": [],    # {page_id, url, prev_title, prev_description}
    }

    # --- CSS theme views ---
    for key in CSS_VIEW_KEYS:
        view = find_view_by_key(client, key)
        if view:
            slug = key.replace(".", "_").replace("-", "_")
            arch_file = os.path.join(backup_dir, f"view_{slug}.arch")
            with open(arch_file, "w", encoding="utf-8") as f:
                f.write(view["arch"])
            manifest["views"].append({
                "action": "update",
                "view_id": view["id"],
                "key": key,
                "arch_file": arch_file,
            })
        else:
            # View doesn't exist yet — rollback = delete it
            manifest["views"].append({
                "action": "would_create",
                "key": key,
                "view_id": None,
                "arch_file": None,
            })

    # --- Page arches ---
    for url in PAGE_URLS:
        pages = client.search_read(
            "website.page",
            [("url", "=", url), ("active", "=", True)],
            ["id", "name", "view_id"],
        )
        if not pages:
            continue
        page = pages[0]
        view_id = page["view_id"]
        if isinstance(view_id, (list, tuple)):
            view_id = view_id[0]
        views = client.read("ir.ui.view", [view_id], ["arch"])
        if views:
            slug = url.strip("/").replace("/", "_") or "home"
            arch_file = os.path.join(backup_dir, f"page_{slug}.arch")
            with open(arch_file, "w", encoding="utf-8") as f:
                f.write(views[0]["arch"])
            manifest["pages"].append({
                "view_id": view_id,
                "url": url,
                "arch_file": arch_file,
            })

    # --- Meta fields ---
    meta_urls = [item["url"] for item in META_UPDATES]
    if meta_urls:
        pages = client.search_read(
            "website.page",
            [("url", "in", meta_urls), ("active", "=", True)],
            ["id", "url", "website_meta_title", "website_meta_description"],
        )
        for page in pages:
            manifest["meta"].append({
                "page_id": page["id"],
                "url": page["url"],
                "prev_title": page.get("website_meta_title") or "",
                "prev_description": page.get("website_meta_description") or "",
            })

    # Write manifest
    manifest_path = os.path.join(backup_dir, "manifest.json")
    with open(manifest_path, "w", encoding="utf-8") as f:
        json.dump(manifest, f, indent=2, ensure_ascii=False)

    return backup_dir


# ---------------------------------------------------------------------------
# Rollback
# ---------------------------------------------------------------------------

def rollback(client, backup_dir):
    """Restore production to the state captured in a backup directory."""
    manifest_path = os.path.join(backup_dir, "manifest.json")
    if not os.path.exists(manifest_path):
        sys.exit(f"ERROR: No manifest.json found in {backup_dir}")

    with open(manifest_path, "r", encoding="utf-8") as f:
        manifest = json.load(f)

    print(f"Rolling back to snapshot from {manifest['timestamp']}")
    print(f"  Source: {manifest['url']} / {manifest['db']}\n")

    # --- Views ---
    for entry in manifest["views"]:
        key = entry["key"]
        action = entry["action"]

        if action == "update":
            # Restore original arch
            arch_file = entry["arch_file"]
            if not arch_file or not os.path.exists(arch_file):
                print(f"  SKIP restore view {key!r} — arch file missing")
                continue
            with open(arch_file, "r", encoding="utf-8") as f:
                arch = f.read()
            # Find the view's current ID on production (may differ from backup if recreated)
            current = find_view_by_key(client, key)
            if current:
                client.write("ir.ui.view", [current["id"]], {"arch": arch})
                print(f"  RESTORED view ID {current['id']} ({key})")
            else:
                print(f"  SKIP restore {key!r} — view no longer exists on production")

        elif action == "would_create":
            # View was created by migration — delete it to restore prior state
            current = find_view_by_key(client, key)
            if current:
                client.unlink("ir.ui.view", [current["id"]])
                print(f"  DELETED view ID {current['id']} ({key}) — did not exist before migration")
            else:
                print(f"  SKIP delete {key!r} — already gone")

    # --- Page arches ---
    for entry in manifest["pages"]:
        arch_file = entry["arch_file"]
        url = entry["url"]
        view_id = entry["view_id"]
        if not arch_file or not os.path.exists(arch_file):
            print(f"  SKIP restore page {url} — arch file missing")
            continue
        with open(arch_file, "r", encoding="utf-8") as f:
            arch = f.read()
        client.write("ir.ui.view", [view_id], {"arch": arch})
        print(f"  RESTORED page arch for {url} (view ID {view_id})")

    # --- Meta ---
    for entry in manifest["meta"]:
        page_id = entry["page_id"]
        url = entry["url"]
        client.write("website.page", [page_id], {
            "website_meta_title": entry["prev_title"],
            "website_meta_description": entry["prev_description"],
        })
        print(f"  RESTORED meta for {url} (page ID {page_id})")

    print("\nRollback complete.")


# ---------------------------------------------------------------------------
# Migration steps
# ---------------------------------------------------------------------------

def migrate_css_view(client, xml_file, view_key, view_name, inherit_key, dry_run):
    """Create or update a CSS-injecting inherit view."""
    if not os.path.exists(xml_file):
        log(f"  SKIP — {os.path.basename(xml_file)} not found", dry_run)
        return

    arch = read_arch_from_xml(xml_file)

    parent = find_view_by_key(client, inherit_key)
    if not parent:
        log(f"  SKIP — parent view {inherit_key!r} not found on production", dry_run)
        return

    parent_id = parent["id"]
    existing = find_view_by_key(client, view_key)

    if existing:
        view_id = existing["id"]
        if not dry_run:
            client.write("ir.ui.view", [view_id], {"arch": arch, "active": True})
        log(
            f"  {'WOULD UPDATE' if dry_run else 'UPDATED'} view ID {view_id} ({view_key})",
            dry_run,
        )
    else:
        vals = {
            "name": view_name,
            "type": "qweb",
            "key": view_key,
            "inherit_id": parent_id,
            "arch": arch,
            "active": True,
        }
        if not dry_run:
            view_id = client.create("ir.ui.view", vals)
            log(f"  CREATED view ID {view_id} ({view_key})", dry_run)
        else:
            log(f"  WOULD CREATE view ({view_key}) inheriting {inherit_key}", dry_run)


def migrate_page_arch(client, url, html_file, dry_run):
    """Update the arch of a page by URL."""
    if not os.path.exists(html_file):
        log(f"  SKIP — {os.path.basename(html_file)} not found", dry_run)
        return

    pages = client.search_read(
        "website.page",
        [("url", "=", url), ("active", "=", True)],
        ["id", "name", "view_id"],
    )
    if not pages:
        log(f"  SKIP — no page at {url}", dry_run)
        return

    page = pages[0]
    view_id = page["view_id"]
    if isinstance(view_id, (list, tuple)):
        view_id = view_id[0]

    with open(html_file, "r", encoding="utf-8") as f:
        content = f.read().strip()
    arch = wrap_arch(content, url, page["name"])

    if not dry_run:
        client.write("ir.ui.view", [view_id], {"arch": arch})
    log(
        f"  {'WOULD UPDATE' if dry_run else 'UPDATED'} view ID {view_id} for {url}",
        dry_run,
    )


def migrate_meta(client, dry_run):
    """Set meta titles and descriptions for all pages in META_UPDATES."""
    for item in META_UPDATES:
        url = item["url"]
        pages = client.search_read(
            "website.page",
            [("url", "=", url), ("active", "=", True)],
            ["id", "name"],
        )
        if not pages:
            log(f"  SKIP meta — no page at {url}", dry_run)
            continue

        page_id = pages[0]["id"]
        vals = {
            "website_meta_title": item["title"],
            "website_meta_description": item["description"],
        }
        if not dry_run:
            client.write("website.page", [page_id], vals)
        log(
            f"  {'WOULD UPDATE' if dry_run else 'UPDATED'} meta for {url} (ID {page_id})",
            dry_run,
        )


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

def main():
    parser = argparse.ArgumentParser(
        description="Migrate staging changes to production"
    )
    mode = parser.add_mutually_exclusive_group()
    mode.add_argument(
        "--dry-run",
        action="store_true",
        help="Show what would be done without making any changes",
    )
    mode.add_argument(
        "--rollback",
        metavar="BACKUP_DIR",
        help="Restore production to a previous backup (e.g. .tmp/prod_backup_20260307_153000)",
    )
    args = parser.parse_args()

    print("\nConnecting to Odoo...")
    client = OdooClient()
    client.authenticate()
    print(f"Connected: {client.url} (db: {client.db})\n")

    # --- Rollback path ---
    if args.rollback:
        backup_dir = args.rollback
        if not os.path.isdir(backup_dir):
            sys.exit(f"ERROR: Backup directory not found: {backup_dir}")
        rollback(client, backup_dir)
        return

    # --- Dry run path ---
    if args.dry_run:
        print("=" * 60)
        print("DRY RUN — no changes will be made")
        print("=" * 60 + "\n")

    # --- Migration path ---
    else:
        print("Backing up current production state...")
        backup_dir = backup_state(client)
        print(f"  Backup saved to: {backup_dir}")
        print(f"  To rollback: python3 tools/migrate_to_production.py --rollback {backup_dir}\n")

    dry_run = args.dry_run

    # Add migration steps here as the project develops.
    #
    # Examples:
    #
    #   print("1. Global brand CSS")
    #   migrate_css_view(
    #       client,
    #       xml_file=os.path.join(TMP, "global_css_current.xml"),
    #       view_key="website.myproject_custom_css",
    #       view_name="My Project Brand CSS",
    #       inherit_key="website.layout",
    #       dry_run=dry_run,
    #   )
    #
    #   print("2. Homepage arch")
    #   migrate_page_arch(
    #       client,
    #       url="/",
    #       html_file=os.path.join(TMP, "draft_home.html"),
    #       dry_run=dry_run,
    #   )
    #
    #   print("3. Meta titles & descriptions")
    #   migrate_meta(client, dry_run)

    print("\n" + "=" * 60)
    if dry_run:
        print("Dry run complete. Run without --dry-run to apply changes.")
    else:
        print("Migration complete.")
        print(f"To rollback: python3 tools/migrate_to_production.py --rollback {backup_dir}")
    print("=" * 60)


if __name__ == "__main__":
    main()
