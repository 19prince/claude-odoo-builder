"""
Pre-push HTML validator for Odoo website pages.

Checks for common mistakes before pushing to Odoo. Uses only stdlib — no extra deps.

Usage:
    python3 tools/validate_html.py --input .tmp/draft_about.html
    echo $?    # 0 = pass, 1 = errors found
"""

import argparse
import re
import sys
from html.parser import HTMLParser

DISALLOWED_ROOT_TAGS = {"html", "head", "body"}
VOID_ELEMENTS = {
    "area", "base", "br", "col", "embed", "hr", "img", "input",
    "link", "meta", "param", "source", "track", "wbr",
}


class OdooHTMLValidator(HTMLParser):
    def __init__(self):
        super().__init__()
        self.errors = []
        self.warnings = []
        self.stack = []
        self.has_editable = False
        self.image_count = 0
        self.images_without_fluid = 0

    def handle_starttag(self, tag, attrs):
        attr_dict = dict(attrs)

        # Check for disallowed root-level tags
        if tag in DISALLOWED_ROOT_TAGS and not self.stack:
            self.errors.append(
                f"Disallowed root tag <{tag}>. "
                "Odoo strips html/head/body — the arch is just inner template content."
            )

        # Check for o_editable
        classes = attr_dict.get("class", "")
        editable_attr = attr_dict.get("o_editable", "")
        if "o_editable" in classes or editable_attr == "1":
            self.has_editable = True

        # Track images
        if tag == "img":
            self.image_count += 1
            if "img-fluid" not in classes:
                self.images_without_fluid += 1

        if tag not in VOID_ELEMENTS:
            self.stack.append(tag)

    def handle_endtag(self, tag):
        if tag in VOID_ELEMENTS:
            return
        if not self.stack:
            self.errors.append(f"Unexpected closing tag </{tag}> — no matching open tag.")
            return
        if self.stack[-1] == tag:
            self.stack.pop()
        else:
            # Look for a matching ancestor
            try:
                idx = len(self.stack) - 1 - list(reversed(self.stack)).index(tag)
                unclosed = self.stack[idx + 1:]
                self.errors.append(
                    f"Closing tag </{tag}> found but <{self.stack[-1]}> was not closed. "
                    f"Unclosed tags: {[f'<{t}>' for t in unclosed]}"
                )
                self.stack = self.stack[:idx]
            except ValueError:
                self.errors.append(
                    f"Closing tag </{tag}> has no matching opening tag."
                )


def check_script_tags(content):
    """Warn about script tags (Odoo strips them from page arch)."""
    issues = []
    if re.search(r"<script", content, re.IGNORECASE):
        issues.append(
            "WARNING: <script> tags found. Odoo may strip these from the page arch. "
            "Use a custom snippet module for JS instead."
        )
    return issues


def check_xss_patterns(content):
    """Warn about HTML patterns that could indicate XSS payloads."""
    issues = []
    if re.search(r'\bon\w+\s*=', content, re.IGNORECASE):
        issues.append(
            "WARNING: Event handler attribute(s) found (onclick, onerror, etc.). "
            "These can be XSS vectors if the content was pasted from an external source."
        )
    if re.search(r'javascript\s*:', content, re.IGNORECASE):
        issues.append(
            "WARNING: javascript: URI found in href or src. "
            "This can execute arbitrary code in the browser."
        )
    if re.search(r'<iframe', content, re.IGNORECASE):
        issues.append(
            "WARNING: <iframe> tag found. "
            "Verify this is intentional — iframes can load external content."
        )
    if re.search(r'<(object|embed)', content, re.IGNORECASE):
        issues.append(
            "WARNING: <object> or <embed> tag found. "
            "These can load external plugins and are rarely needed in Odoo pages."
        )
    return issues


def check_qweb_wrapper(content):
    """Warn if the arch is not wrapped in a QWeb t-name template."""
    warnings = []
    stripped = content.strip()
    if not stripped.startswith('<t t-name='):
        warnings.append(
            "WARNING: Arch does not start with <t t-name=...>. "
            "push_page.py will auto-wrap it, but verify the page key is correct."
        )
    return warnings


def validate(content):
    parser = OdooHTMLValidator()
    try:
        parser.feed(content)
    except Exception as e:
        parser.errors.append(f"Parse error: {e}")

    warnings = []
    errors = list(parser.errors)

    # Unclosed tags at end of doc
    if parser.stack:
        errors.append(
            f"Unclosed tags at end of file: {[f'<{t}>' for t in parser.stack]}"
        )

    # Editability
    if not parser.has_editable:
        warnings.append(
            "WARNING: No o_editable class or attribute found. "
            "Content regions won't be editable in the Odoo WYSIWYG editor. "
            "Add class='o_editable' or o_editable=\"1\" to text containers."
        )

    # Images
    if parser.images_without_fluid > 0:
        warnings.append(
            f"WARNING: {parser.images_without_fluid}/{parser.image_count} image(s) "
            "are missing class='img-fluid'. Images may overflow on mobile."
        )

    warnings.extend(check_script_tags(content))
    warnings.extend(check_xss_patterns(content))
    warnings.extend(check_qweb_wrapper(content))

    return errors, warnings


def main():
    parser = argparse.ArgumentParser(description="Validate HTML for Odoo compatibility")
    parser.add_argument("--input", required=True, help="Path to HTML file to validate")
    args = parser.parse_args()

    if not __import__("os").path.exists(args.input):
        print(f"ERROR: File not found: {args.input}")
        sys.exit(1)

    with open(args.input, "r", encoding="utf-8") as f:
        content = f.read()

    errors, warnings = validate(content)

    for w in warnings:
        print(w)

    if errors:
        print()
        for e in errors:
            print(f"ERROR: {e}")
        print(f"\nValidation FAILED ({len(errors)} error(s), {len(warnings)} warning(s)).")
        sys.exit(1)
    else:
        print(f"Validation PASSED ({len(warnings)} warning(s)).")
        sys.exit(0)


if __name__ == "__main__":
    main()
