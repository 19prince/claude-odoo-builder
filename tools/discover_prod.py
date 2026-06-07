"""
Discover production site state for migration planning.

Outputs website ID, top menu ID, current nav items, homepage view ID,
whether /resources exists, and current custom_code_head length.

Saves results to .tmp/prod_discovery.json.
"""

import json
import os
import sys
from urllib.parse import urlparse

from dotenv import load_dotenv

load_dotenv(os.path.join(os.path.dirname(__file__), "..", ".env"))

sys.path.insert(0, os.path.dirname(__file__))
from odoo_client import OdooClient

TMP = os.path.join(os.path.dirname(__file__), "..", ".tmp")


def main():
    raw_url = os.getenv("PROD_ODOO_URL", "").rstrip("/")
    parsed = urlparse(raw_url)
    prod_url = f"{parsed.scheme}://{parsed.netloc}"
    prod_db = os.getenv("PROD_ODOO_DB", "")
    prod_user = os.getenv("PROD_ODOO_USER", "")
    prod_pass = os.getenv("PROD_ODOO_PASSWORD", "")

    missing = [k for k, v in [
        ("PROD_ODOO_URL", prod_url), ("PROD_ODOO_DB", prod_db),
        ("PROD_ODOO_USER", prod_user), ("PROD_ODOO_PASSWORD", prod_pass),
    ] if not v]
    if missing:
        sys.exit(f"ERROR: Missing in .env: {', '.join(missing)}")

    print(f"Connecting to {prod_url} ...")
    client = OdooClient(url=prod_url, db=prod_db, user=prod_user, password=prod_pass)
    client.authenticate()
    print("Authenticated.\n")

    discovery = {}

    # 1. Website ID
    sites = client.search_read("website", [], ["id", "name", "domain", "custom_code_head"])
    site = sites[0]
    site_id = site["id"]
    head_len = len(site.get("custom_code_head") or "")
    discovery["website_id"] = site_id
    discovery["website_name"] = site["name"]
    discovery["website_domain"] = site.get("domain")
    discovery["custom_code_head_length"] = head_len
    print(f"Website: '{site['name']}' (ID {site_id}), custom_code_head: {head_len} chars")

    # Backup current custom_code_head
    head_content = site.get("custom_code_head") or ""
    if head_content:
        backup_path = os.path.join(TMP, "prod_backup_custom_code_head.txt")
        with open(backup_path, "w", encoding="utf-8") as f:
            f.write(head_content)
        print(f"  Backed up to {backup_path}")

    # 2. Top menu parent ID
    root_menus = client.search_read(
        "website.menu",
        [("website_id", "=", site_id), ("parent_id", "=", False)],
        ["id", "name", "url"],
    )
    print(f"\nRoot menus: {root_menus}")

    top_menu = None
    if root_menus:
        top_menu = root_menus[0]
        discovery["top_menu_id"] = top_menu["id"]
        discovery["top_menu_name"] = top_menu["name"]

    # 3. Current nav items
    if top_menu:
        nav_items = client.search_read(
            "website.menu",
            [("parent_id", "=", top_menu["id"])],
            ["id", "name", "url", "sequence", "mega_menu_content"],
        )
        nav_items.sort(key=lambda x: x["sequence"])
        discovery["nav_items"] = []
        print(f"\nNav items under menu ID {top_menu['id']}:")
        for item in nav_items:
            has_mega = "YES" if item.get("mega_menu_content") else "no"
            print(f"  [{item['id']}] seq={item['sequence']:3d}  mega={has_mega}  {item['name']!r}  →  {item['url']}")
            discovery["nav_items"].append({
                "id": item["id"],
                "name": item["name"],
                "url": item["url"],
                "sequence": item["sequence"],
                "has_mega": bool(item.get("mega_menu_content")),
            })

    # 4. Homepage view ID
    home_pages = client.search_read(
        "website.page",
        [("url", "=", "/"), ("website_id", "=", site_id)],
        ["id", "name", "view_id", "website_published"],
    )
    if not home_pages:
        home_pages = client.search_read(
            "website.page",
            [("url", "=", "/"), ("active", "=", True)],
            ["id", "name", "view_id", "website_published"],
        )
    discovery["homepage"] = None
    if home_pages:
        hp = home_pages[0]
        vid = hp["view_id"]
        if isinstance(vid, (list, tuple)):
            vid = vid[0]
        discovery["homepage"] = {"page_id": hp["id"], "view_id": vid, "name": hp["name"], "published": hp["website_published"]}
        print(f"\nHomepage: page_id={hp['id']}, view_id={vid}, name={hp['name']!r}, published={hp['website_published']}")
    else:
        print("\nHomepage: NOT FOUND")

    # 5. Resources page
    res_pages = client.search_read(
        "website.page",
        [("url", "=", "/resources"), ("website_id", "=", site_id)],
        ["id", "name", "view_id", "website_published"],
    )
    if not res_pages:
        res_pages = client.search_read(
            "website.page",
            [("url", "=", "/resources"), ("active", "=", True)],
            ["id", "name", "view_id", "website_published"],
        )
    discovery["resources_page"] = None
    if res_pages:
        rp = res_pages[0]
        vid = rp["view_id"]
        if isinstance(vid, (list, tuple)):
            vid = vid[0]
        discovery["resources_page"] = {"page_id": rp["id"], "view_id": vid, "name": rp["name"], "published": rp["website_published"]}
        print(f"Resources: page_id={rp['id']}, view_id={vid}, name={rp['name']!r}, published={rp['website_published']}")
    else:
        print("Resources page: NOT FOUND (will need to create)")

    # 6. Check if key linked pages exist
    for url in ["/odoo-icp-module", "/claude-code-skill", "/about", "/blog", "/contactus", "/services"]:
        pages = client.search_read(
            "website.page",
            [("url", "=", url), ("active", "=", True)],
            ["id", "name", "website_published"],
        )
        status = f"page_id={pages[0]['id']}, published={pages[0]['website_published']}" if pages else "NOT FOUND"
        print(f"  {url}: {status}")

    # Save
    out_path = os.path.join(TMP, "prod_discovery.json")
    with open(out_path, "w", encoding="utf-8") as f:
        json.dump(discovery, f, indent=2, ensure_ascii=False)
    print(f"\nSaved to {out_path}")


if __name__ == "__main__":
    main()
