"""
Generate a complete Odoo custom snippet module skeleton.

Usage:
    python3 tools/scaffold_snippet.py --name hero_split_screen --label "Hero Split Screen"
    python3 tools/scaffold_snippet.py --name pricing_table --label "Pricing Table" --odoo-version 17

Output: .tmp/snippets/{name}/ — a full installable Odoo module
"""

import argparse
import os
import sys
import textwrap

DEFAULT_ODOO_VERSION = 17

MANIFEST = """\
{{
    'name': '{label}',
    'version': '1.0',
    'summary': 'Custom website snippet: {label}',
    'category': 'Website',
    'depends': ['website'],
    'data': [
        'views/snippets.xml',
        'views/assets.xml',
    ],
    'assets': {{
        'web.assets_frontend': [
            '{name}/static/src/scss/snippet.scss',
            '{name}/static/src/js/snippet.js',
        ],
    }},
    'installable': True,
    'auto_install': False,
    'license': 'LGPL-3',
}}
"""

INIT_PY = ""  # empty __init__.py

SNIPPETS_XML = """\
<?xml version="1.0" encoding="utf-8"?>
<odoo>

  <!-- ============================================================
       Snippet Template
       CSS class: .s_{name}
       Usage: drag from Website Editor snippet panel
  ============================================================ -->
  <template id="s_{name}" name="{label}">
    <section class="s_{name} o_colored_level py-5"
             data-snippet="{name}.s_{name}"
             data-name="{label}">
      <div class="container">
        <div class="row align-items-center g-5">
          <div class="col-lg-6">
            <h2 class="fw-bold o_editable">Section Headline</h2>
            <p class="lead text-muted o_editable">
              Supporting paragraph — describe the value in two or three sentences.
            </p>
            <a href="#" class="btn btn-primary mt-3 o_editable">Get Started</a>
          </div>
          <div class="col-lg-6 text-center">
            <img
              src="https://placehold.co/560x400/EEF/336?text={label}"
              class="img-fluid rounded shadow"
              alt=""
            />
          </div>
        </div>
      </div>
    </section>
  </template>

  <!-- ============================================================
       Register snippet in the Website Editor panel
  ============================================================ -->
  <template id="snippets_registration" inherit_id="website.snippets" priority="8">
    <xpath expr="//div[@id='snippet_content']//t[@t-snippet][last()]" position="after">
      <t t-snippet="{name}.s_{name}" t-thumbnail="/web/image?model=website.snippet&amp;field=image_512"/>
    </xpath>
  </template>

</odoo>
"""

ASSETS_XML = """\
<?xml version="1.0" encoding="utf-8"?>
<odoo>
  <!-- Assets are registered in __manifest__.py 'assets' key (Odoo 15+).
       This file is kept as a reference / fallback for older Odoo versions.
       For Odoo 14 and below, uncomment the block below and remove 'assets'
       from __manifest__.py. -->

  <!--
  <template id="assets_frontend" inherit_id="website.assets_frontend" name="{label} Assets">
    <xpath expr="." position="inside">
      <link rel="stylesheet" href="/{name}/static/src/scss/snippet.scss"/>
      <script type="text/javascript" src="/{name}/static/src/js/snippet.js"/>
    </xpath>
  </template>
  -->
</odoo>
"""

SNIPPET_SCSS = """\
// {label} — custom snippet styles
// Root selector: .s_{name}
// All rules must be scoped under this class to avoid polluting global styles.

.s_{name} {{
  // Default padding is set via Bootstrap utility classes (py-5) in the template.
  // Add overrides here.

  h2 {{
    // Inherits from Bootstrap / Odoo theme font stack.
  }}

  img {{
    max-width: 100%;
  }}

  // Example modifier classes (apply via snippet options panel in the editor)
  // &.dark-variant {{
  //   background-color: var(--color-primary);
  //   color: #fff;
  // }}
}}
"""

SNIPPET_JS = """\
/** {label} — custom snippet JavaScript
 *
 * Only add code here if this snippet requires interactivity.
 * For static HTML+CSS snippets, this file can remain empty.
 *
 * Odoo 15+ uses OWL; Odoo 14 uses legacy widget system.
 * Example (OWL component, Odoo 15+):
 *
 *   import {{ Component }} from '@odoo/owl';
 *   import {{ registry }} from '@web/core/registry';
 *
 *   class {class_name}Snippet extends Component {{
 *     static template = xml`<t t-slot="default"/>`;
 *   }}
 *
 *   registry.category('public_components').add('{name}.{class_name}Snippet', {{
 *     component: {class_name}Snippet,
 *   }});
 */
"""


def to_class_name(snake):
    return "".join(word.capitalize() for word in snake.split("_"))


def write_file(path, content):
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "w", encoding="utf-8") as f:
        f.write(content)
    print(f"  created: {os.path.relpath(path)}")


def scaffold(name, label, odoo_version, out_dir):
    class_name = to_class_name(name)
    ctx = {"name": name, "label": label, "class_name": class_name}

    files = {
        "__manifest__.py": MANIFEST.format(**ctx),
        "__init__.py": INIT_PY,
        "views/snippets.xml": SNIPPETS_XML.format(**ctx),
        "views/assets.xml": ASSETS_XML.format(**ctx),
        "static/src/scss/snippet.scss": SNIPPET_SCSS.format(**ctx),
        "static/src/js/snippet.js": SNIPPET_JS.format(**ctx),
    }

    root = os.path.join(out_dir, name)
    print(f"\nScaffolding snippet module: {name}")
    print(f"Output directory: {root}\n")

    for rel_path, content in files.items():
        write_file(os.path.join(root, rel_path), content)

    print(f"\nDone. Next steps:")
    print(f"  1. Customize .tmp/snippets/{name}/views/snippets.xml (HTML template)")
    print(f"  2. Add styles in .tmp/snippets/{name}/static/src/scss/snippet.scss")
    print(f"  3. Copy the {name}/ folder to your Odoo server's custom addons path")
    print(f"  4. In Odoo: Apps -> Update Apps List -> search '{name}' -> Install")
    print(f"  5. Open Website Editor -> drag '{label}' from the snippet panel")


def main():
    parser = argparse.ArgumentParser(description="Scaffold an Odoo custom snippet module")
    parser.add_argument("--name", required=True, help="Technical name, snake_case (e.g. hero_split_screen)")
    parser.add_argument("--label", required=True, help="Display name (e.g. 'Hero Split Screen')")
    parser.add_argument(
        "--odoo-version",
        type=int,
        default=DEFAULT_ODOO_VERSION,
        help=f"Odoo major version (default: {DEFAULT_ODOO_VERSION})",
    )
    args = parser.parse_args()

    if not args.name.replace("_", "").isalnum():
        sys.exit("ERROR: --name must be snake_case alphanumeric (e.g. hero_split_screen)")

    out_dir = os.path.join(os.path.dirname(__file__), "..", ".tmp", "snippets")
    scaffold(args.name, args.label, args.odoo_version, out_dir)


if __name__ == "__main__":
    main()
