# Workflow: Design and create an Odoo survey

Use this when the user wants to launch a survey via the Odoo Surveys app — webinar input, customer research, NPS, partner pulse, lead-gen quiz, etc.

The tool is `tools/create_survey.py`. It reads a YAML definition file and creates the survey + questions + answer options on Odoo via JSON-RPC. Existing surveys can be replaced with `--update --id N`.

---

## 1. Orient

Confirm the brief:

- **Purpose** — what decision or content does the survey power? (Webinar reveal? Lead routing? Customer research?)
- **Audience** — public link (anyone) or token (invited people only)?
- **Length** — how many questions? Anything over ~10 starts hurting completion.
- **Live or draft** — Odoo 18 has no `state` field on surveys. The survey "goes live" simply by sharing the URL. Until you share, it's effectively private.

---

## 2. Plan questions

Map each question's intent to an Odoo `question_type`:

| Intent                              | `question_type`     | Notes                                              |
|-------------------------------------|---------------------|----------------------------------------------------|
| "Pick one"                          | `simple_choice`     | Renders as radio buttons.                          |
| "Pick all that apply"               | `multiple_choice`   | Renders as checkboxes.                             |
| One sentence (~140 chars)           | `char_box`          | Single-line input. **No char-limit field in 18.**  |
| Several sentences                   | `text_box`          | Textarea.                                          |
| Number                              | `numerical_box`     | Optional `validation_min/max_float_value`.         |
| 1–10 rating                         | `scale`             | Built-in scale widget.                             |
| Date / datetime                     | `date` / `datetime` | Date picker.                                       |

**Required vs optional:** set `required: true` on questions you must have data for. Use sparingly — every required question increases drop-off.

---

## 3. Write the YAML

Save to `.tmp/survey_<slug>.yaml`. Example:

```yaml
title: "Customer Feedback"
description: "<p>A quick pulse on how things are going. ~2 minutes.</p>"
access_mode: public                  # public | token
users_login_required: false
users_can_go_back: false
questions_layout: page_per_section   # one_page | page_per_section | page_per_question
questions_selection: all
scoring_type: no_scoring

questions:
  - title: "How likely are you to recommend us to a colleague?"
    question_type: scale
    required: true

  - title: "Which of the following describes your role? (check all that apply)"
    question_type: multiple_choice
    required: true
    options:
      - "Decision-maker"
      - "End user"
      - "Implementer / IT"
      - "Other"

  - title: "What's the single biggest thing we could improve?"
    question_type: char_box
    required: false
    description: "<p>One sentence is plenty.</p>"

  - title: "Any other feedback you'd like to share?"
    question_type: text_box
    required: false
```

**Internal "Why:" notes / headline-planning rationale** belong in a sidecar file, not in Odoo:

`.tmp/survey_<slug>_notes.md` — human-only planning doc. Keeps strategic intent out of any field that respondents can see.

---

## 4. Dry-run

```bash
python3 tools/create_survey.py --file .tmp/survey_<slug>.yaml --dry-run
```

Inspect the printed payload. Confirm:

- Top-level required fields (`title`, `access_mode`, `questions_layout`, `questions_selection`, `scoring_type`) are present.
- Each question has a `question_type` and the right `constr_mandatory` boolean.
- Choice questions have a `suggested_answer_ids` list with `(0, 0, {value, sequence})` tuples.
- Total question count and answer-option count match expectations.

---

## 5. Push to Odoo

```bash
python3 tools/create_survey.py --file .tmp/survey_<slug>.yaml
```

The tool prints the survey ID, the public URL (`{ODOO_URL}/survey/start/<access_token>`), and the backend admin URL.

---

## 6. Review in the Odoo UI

Open the backend URL printed above (Surveys app → your survey). Click **Test** to walk through it as a respondent. Check:

- Title and intro description render.
- Question order matches the YAML.
- Choice questions show the right control (radio vs checkbox).
- Char/text inputs accept the right shape.
- Required questions block submission when empty.

If anything is off, fix the YAML and re-push with `--update --id N`. Note: this deletes and recreates all questions — you'll be prompted to confirm. Pass `--yes` to skip the prompt in scripted contexts.

---

## 7. Share

The public URL is the share link. In Odoo 18, surveys do not need to be "opened" — the URL works as soon as the survey exists. Distribute via email, social, embedded buttons, etc.

To stop accepting responses, archive the survey in the Odoo UI (Action → Archive), or `client.write("survey.survey", [id], {"active": False})`.

---

## Gotchas (Odoo 18)

- **No `state` field** on `survey.survey`. Surveys are not draft/open/closed.
- **No `validation_max_text_length`** field on `survey.question`. To suggest a length on a `char_box`, put it in the question `description` HTML.
- **`access_token` is required for the public URL.** It's auto-generated on create; the tool reads it back and prints the URL.
- **`--update` deletes existing questions** before recreating them. Any answers respondents have already submitted will be orphaned. The tool prompts for `yes` confirmation before deleting and warns when existing `survey.user_input` records are present; pass `--yes` only when you're sure.

---

## Reusable steps for next time

1. Read this workflow.
2. Capture the survey brief.
3. Write `.tmp/survey_<slug>.yaml` (and `.tmp/survey_<slug>_notes.md` for any internal rationale).
4. Dry-run.
5. Push.
6. Test in Odoo UI.
7. Share the public URL.
