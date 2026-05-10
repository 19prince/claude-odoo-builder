"""
Create or update an Odoo survey from a YAML definition file.

YAML schema (Odoo 18+):

    title: "My Survey"
    description: "<p>HTML intro shown on the landing page (optional).</p>"
    access_mode: public                 # public | token
    users_login_required: false
    users_can_go_back: false
    questions_layout: page_per_section  # one_page | page_per_section | page_per_question
    questions_selection: all            # all | random
    scoring_type: no_scoring

    questions:
      - title: "Pick one"
        question_type: simple_choice    # simple_choice | multiple_choice |
                                        # char_box | text_box | numerical_box |
                                        # scale | date | datetime
        required: true                  # → constr_mandatory
        description: "<p>Per-question help (optional)</p>"
        options:                        # only for simple_choice / multiple_choice
          - "Option A"
          - "Option B"

Usage:
    python3 tools/create_survey.py --file .tmp/survey.yaml                    # create
    python3 tools/create_survey.py --file .tmp/survey.yaml --dry-run          # show payload only
    python3 tools/create_survey.py --file .tmp/survey.yaml --update --id 12   # replace existing

Notes for Odoo 18:
  - There is no `state` field on `survey.survey` — surveys are not draft/open/closed.
    Sharing the access URL is what makes a survey "live".
  - There is no `validation_max_text_length` field on `survey.question`. Single-line
    character limits cannot be enforced server-side; mention any soft limit in the
    question description instead.
"""

import argparse
import json
import os
import sys

sys.path.insert(0, os.path.dirname(__file__))
from odoo_client import OdooClient  # noqa: E402

try:
    import yaml
except ImportError:
    sys.exit(
        "ERROR: PyYAML is required. Install with: pip install pyyaml"
    )


CHOICE_TYPES = {"simple_choice", "multiple_choice"}
ALLOWED_TYPES = CHOICE_TYPES | {
    "char_box",
    "text_box",
    "numerical_box",
    "scale",
    "date",
    "datetime",
}

SURVEY_PASSTHROUGH_FIELDS = {
    "title",
    "description",
    "access_mode",
    "users_login_required",
    "users_can_go_back",
    "users_can_signup",
    "questions_layout",
    "questions_selection",
    "scoring_type",
    "is_attempts_limited",
    "attempts_limit",
    "is_time_limited",
    "time_limit",
    "certification",
}

QUESTION_PASSTHROUGH_FIELDS = {
    "title",
    "question_type",
    "description",
    "constr_mandatory",
    "constr_error_msg",
    "sequence",
    "is_page",
    "answer_score",
    "validation_email",
    "validation_min_float_value",
    "validation_max_float_value",
    "validation_min_date",
    "validation_max_date",
}


def validate(spec):
    if not isinstance(spec, dict):
        raise ValueError("Top-level YAML must be a mapping.")
    if not spec.get("title"):
        raise ValueError("Survey 'title' is required.")
    questions = spec.get("questions") or []
    if not questions:
        raise ValueError("At least one question is required.")
    for i, q in enumerate(questions, 1):
        loc = f"question #{i}"
        if not isinstance(q, dict):
            raise ValueError(f"{loc}: must be a mapping.")
        if not q.get("title"):
            raise ValueError(f"{loc}: 'title' is required.")
        qtype = q.get("question_type") or q.get("type")
        if not qtype:
            raise ValueError(f"{loc}: 'question_type' is required.")
        if qtype not in ALLOWED_TYPES:
            raise ValueError(
                f"{loc}: question_type '{qtype}' is not supported. "
                f"Allowed: {sorted(ALLOWED_TYPES)}"
            )
        if qtype in CHOICE_TYPES:
            opts = q.get("options") or []
            if len(opts) < 2:
                raise ValueError(
                    f"{loc}: choice questions need at least 2 'options'."
                )


def build_question_payload(q):
    qtype = q.get("question_type") or q.get("type")
    payload = {"question_type": qtype}

    for field in QUESTION_PASSTHROUGH_FIELDS:
        if field in q and field != "question_type":
            payload[field] = q[field]

    if "required" in q:
        payload["constr_mandatory"] = bool(q["required"])

    if qtype in CHOICE_TYPES:
        opts = q.get("options") or []
        payload["suggested_answer_ids"] = [
            (0, 0, {"value": str(opt), "sequence": idx + 1})
            for idx, opt in enumerate(opts)
        ]

    return payload


def build_survey_payload(spec):
    payload = {
        "access_mode": "public",
        "questions_layout": "page_per_section",
        "questions_selection": "all",
        "scoring_type": "no_scoring",
    }
    for field in SURVEY_PASSTHROUGH_FIELDS:
        if field in spec:
            payload[field] = spec[field]

    questions = spec.get("questions") or []
    payload["question_and_page_ids"] = [
        (0, 0, {**build_question_payload(q), "sequence": idx + 1})
        for idx, q in enumerate(questions)
    ]
    return payload


def cmd_create(client, payload, base_url):
    survey_id = client.create("survey.survey", payload)
    print(f"Created survey ID: {survey_id}")
    print_link(client, survey_id, base_url)
    return survey_id


def cmd_update(client, survey_id, payload, base_url, assume_yes=False):
    existing = client.search_read(
        "survey.survey", [("id", "=", survey_id)], ["id", "title"]
    )
    if not existing:
        sys.exit(f"ERROR: No survey found with id={survey_id}")

    old_questions = client.search(
        "survey.question", [("survey_id", "=", survey_id)]
    )
    response_count = len(client.search(
        "survey.user_input", [("survey_id", "=", survey_id)]
    ))

    if old_questions or response_count:
        print(
            f"WARNING: --update will DELETE {len(old_questions)} existing question(s) "
            f"on survey id={survey_id} ({existing[0]['title']!r})."
        )
        if response_count:
            print(
                f"WARNING: this survey already has {response_count} respondent "
                f"submission(s). Deleting questions may orphan their answers."
            )
        if not assume_yes:
            try:
                reply = input("Type 'yes' to continue, anything else to abort: ").strip().lower()
            except EOFError:
                reply = ""
            if reply != "yes":
                sys.exit("Aborted — no changes made.")

    if old_questions:
        client.unlink("survey.question", old_questions)
        print(f"Removed {len(old_questions)} existing question(s).")

    questions_payload = payload.pop("question_and_page_ids", [])
    if questions_payload:
        payload["question_and_page_ids"] = questions_payload
    client.write("survey.survey", [survey_id], payload)
    print(f"Updated survey ID: {survey_id}")
    print_link(client, survey_id, base_url)
    return survey_id


def print_link(client, survey_id, base_url):
    rec = client.read("survey.survey", [survey_id], ["title", "access_token", "access_mode"])
    if not rec:
        return
    r = rec[0]
    token = r.get("access_token") or ""
    if token:
        url = f"{base_url}/survey/start/{token}"
        print(f"Title:  {r['title']}")
        print(f"Access: {r.get('access_mode')}")
        print(f"URL:    {url}")
        print(f"Backend: {base_url}/odoo/surveys/{survey_id}")
    else:
        print(f"Title: {r['title']}  (no access_token returned — check the Odoo backend)")


def main():
    parser = argparse.ArgumentParser(description="Create an Odoo survey from a YAML definition")
    parser.add_argument("--file", required=True, help="Path to survey YAML file")
    parser.add_argument("--dry-run", action="store_true", help="Print payload, do not write")
    parser.add_argument("--update", action="store_true", help="Update an existing survey")
    parser.add_argument("--id", type=int, help="Survey ID for --update")
    parser.add_argument("--yes", action="store_true", help="Skip the destructive --update confirmation prompt")

    args = parser.parse_args()
    if args.update and not args.id:
        sys.exit("ERROR: --update requires --id")

    if not os.path.exists(args.file):
        sys.exit(f"ERROR: File not found: {args.file}")

    with open(args.file, "r", encoding="utf-8") as f:
        spec = yaml.safe_load(f)

    validate(spec)
    payload = build_survey_payload(spec)

    if args.dry_run:
        print(json.dumps(payload, indent=2, ensure_ascii=False, default=str))
        n_q = len(spec.get("questions") or [])
        n_opts = sum(
            len(q.get("options") or [])
            for q in (spec.get("questions") or [])
            if (q.get("question_type") or q.get("type")) in CHOICE_TYPES
        )
        print(f"\nDRY RUN — {n_q} questions, {n_opts} answer options.")
        return

    client = OdooClient()
    client.authenticate()

    if args.update:
        cmd_update(client, args.id, payload, client.url, assume_yes=args.yes)
    else:
        cmd_create(client, payload, client.url)


if __name__ == "__main__":
    main()
