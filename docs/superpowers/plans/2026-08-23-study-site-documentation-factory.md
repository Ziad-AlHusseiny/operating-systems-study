# Study Website Documentation Factory Kit Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Build a validated, reusable documentation factory kit that turns new learning materials into the same simple study-website product, including Material lessons and generated exam-quality MCQ and True/False questions.

**Architecture:** Store the reusable human/agent instructions as a numbered Markdown pack under `docs/study-site-factory/`, with machine-readable JSON examples under `examples/`. Add a Python standard-library validator that checks required files, JSON examples, documented template variables, required headings, and internal Markdown links so the kit remains internally consistent and reusable.

**Tech Stack:** Markdown, JSON, Python 3 standard library, `unittest`, Git.

**Spec:** `docs/superpowers/specs/2026-08-20-study-site-documentation-factory-design.md`

## Global Constraints

- Support repeated use across roughly 20 independent study websites.
- Accept PDF, DOCX, PPTX, text, Markdown, CSV, JSON, and image materials.
- Keep HTML, CSS, vanilla JavaScript, JSON, and LocalStorage as the default website architecture.
- Keep official source content, generated guidance, and generated questions structurally and visibly separate.
- Give every learning claim and generated question a file plus page, slide, section, row, or image reference.
- Preserve uncertainty; unsupported, conflicting, or contradictory content remains review-only and unscored.
- Add a Material section with lessons, objectives, summaries, explanations, terms, examples, mistakes, exam tips, recaps, sources, and linked questions.
- Define exam-quality MCQ and True/False generation, evidence, difficulty, cognitive level, duplication, and review rules.
- Use uppercase double-brace template variables and document every variable used by the kit.
- Make the workflow resumable through stage artifacts, reports, deterministic builders, check modes, and a progress ledger.
- Cover automated validation, browser QA, accessibility, deployment, and public verification.
- Do not add a backend, framework, account system, database, or CLI scaffolder.

---

## File Map

| File | Responsibility |
|---|---|
| `docs/study-site-factory/README.md` | Kit overview, reading map, operating principles, and file index. |
| `docs/study-site-factory/00-QUICK-START.md` | Minimal repeatable steps for starting one new website. |
| `docs/study-site-factory/01-PROJECT-INPUT-TEMPLATE.md` | Human-completed brief and complete template-variable dictionary. |
| `docs/study-site-factory/02-PRD-TEMPLATE.md` | Stable product requirements with configurable values isolated. |
| `docs/study-site-factory/03-SOURCE-INGESTION-SPEC.md` | Format-specific extraction, rendering, provenance, OCR, duplicates, and source-audit rules. |
| `docs/study-site-factory/04-CONTENT-AND-DATA-CONTRACTS.md` | Exact record families, field tables, ID conventions, boundaries, validation, and progress compatibility. |
| `docs/study-site-factory/05-MATERIAL-LESSONS-SPEC.md` | Material information architecture, lesson authoring model, route behavior, and lesson QA. |
| `docs/study-site-factory/06-QUESTION-GENERATION-SPEC.md` | MCQ and True/False authoring rubrics, distributions, evidence, review states, and rejection rules. |
| `docs/study-site-factory/07-UX-AND-SYSTEM-FLOW.md` | Navigation, user journeys, responsive behavior, accessibility, and official/generated labeling. |
| `docs/study-site-factory/08-BUILD-WORKFLOW.md` | Stage-by-stage, resumable implementation workflow and artifact ledger. |
| `docs/study-site-factory/09-QA-GATES.md` | Eight blocking QA gates, exact evidence, commands, and report format. |
| `docs/study-site-factory/10-MASTER-BUILD-PROMPT.md` | Copy-ready agent prompt that reads the kit progressively and executes one project. |
| `docs/study-site-factory/11-HANDOFF-AND-DEPLOYMENT.md` | Maintainer handoff, content corrections, GitHub Pages, and public verification. |
| `docs/study-site-factory/examples/project-config.example.json` | All configurable project values with realistic defaults. |
| `docs/study-site-factory/examples/source-manifest.example.json` | One normalized source inventory with multiple location types. |
| `docs/study-site-factory/examples/lesson.example.json` | Complete generated lesson record. |
| `docs/study-site-factory/examples/official-question.example.json` | Complete official source question with provenance and review state. |
| `docs/study-site-factory/examples/generated-question.example.json` | Complete generated MCQ with evidence and quality metadata. |
| `docs/study-site-factory/examples/explanation.example.json` | Separate translated question guidance record. |
| `scripts/validate_factory_kit.py` | Read-only validation of structure, JSON, variables, headings, links, and banned unfinished markers. |
| `scripts/test_validate_factory_kit.py` | Unit and production-artifact tests for the kit validator. |

---

### Task 1: Build the validator and foundation documents

**Files:**
- Create: `scripts/validate_factory_kit.py`
- Create: `scripts/test_validate_factory_kit.py`
- Create: `docs/study-site-factory/README.md`
- Create: `docs/study-site-factory/00-QUICK-START.md`
- Create: `docs/study-site-factory/01-PROJECT-INPUT-TEMPLATE.md`
- Create: `docs/study-site-factory/examples/project-config.example.json`

**Interfaces:**
- Consumes: the approved design specification and this plan's File Map.
- Produces: `collect_template_variables(text: str) -> set[str]`, `validate_json_file(path: Path) -> list[str]`, `validate_required_files(root: Path, required: tuple[str, ...]) -> list[str]`, `validate_markdown_headings(path: Path, required: tuple[str, ...]) -> list[str]`, `validate_internal_links(root: Path, markdown_paths: list[Path]) -> list[str]`, and `validate_kit(root: Path) -> list[str]`.

- [ ] **Step 1: Write failing validator unit tests**

Create `scripts/test_validate_factory_kit.py` with temporary-directory tests that import the real validator:

```python
import json
import tempfile
import unittest
from pathlib import Path

from scripts.validate_factory_kit import (
    collect_template_variables,
    validate_json_file,
    validate_required_files,
)


class FactoryKitValidatorTests(unittest.TestCase):
    def test_collects_uppercase_double_brace_variables(self):
        text = "{{PROJECT_TITLE}} {{STUDY_LANGUAGE}} {{PROJECT_TITLE}}"
        self.assertEqual(
            collect_template_variables(text),
            {"PROJECT_TITLE", "STUDY_LANGUAGE"},
        )

    def test_reports_missing_required_files(self):
        with tempfile.TemporaryDirectory() as directory:
            errors = validate_required_files(
                Path(directory),
                ("README.md", "examples/project-config.example.json"),
            )
        self.assertEqual(len(errors), 2)

    def test_reports_invalid_json(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "bad.json"
            path.write_text("{", encoding="utf-8")
            self.assertTrue(validate_json_file(path))


if __name__ == "__main__":
    unittest.main()
```

- [ ] **Step 2: Run the validator tests and verify RED**

Run:

```powershell
python -B -m unittest scripts.test_validate_factory_kit -v
```

Expected: import failure because `scripts/validate_factory_kit.py` does not exist.

- [ ] **Step 3: Implement the reusable validator primitives**

Create `scripts/validate_factory_kit.py` with these constants and signatures:

```python
import argparse
import json
import re
from pathlib import Path

VARIABLE = re.compile(r"\{\{([A-Z][A-Z0-9_]*)\}\}")

REQUIRED_DOCS = (
    "README.md",
    "00-QUICK-START.md",
    "01-PROJECT-INPUT-TEMPLATE.md",
    "02-PRD-TEMPLATE.md",
    "03-SOURCE-INGESTION-SPEC.md",
    "04-CONTENT-AND-DATA-CONTRACTS.md",
    "05-MATERIAL-LESSONS-SPEC.md",
    "06-QUESTION-GENERATION-SPEC.md",
    "07-UX-AND-SYSTEM-FLOW.md",
    "08-BUILD-WORKFLOW.md",
    "09-QA-GATES.md",
    "10-MASTER-BUILD-PROMPT.md",
    "11-HANDOFF-AND-DEPLOYMENT.md",
)

REQUIRED_EXAMPLES = (
    "examples/project-config.example.json",
    "examples/source-manifest.example.json",
    "examples/lesson.example.json",
    "examples/official-question.example.json",
    "examples/generated-question.example.json",
    "examples/explanation.example.json",
)


def collect_template_variables(text: str) -> set[str]:
    return set(VARIABLE.findall(text))


def validate_json_file(path: Path) -> list[str]:
    try:
        json.loads(path.read_text(encoding="utf-8"))
    except (OSError, UnicodeError, json.JSONDecodeError) as error:
        return [f"{path}: invalid JSON: {error}"]
    return []


def validate_required_files(root: Path, required: tuple[str, ...]) -> list[str]:
    return [f"missing required file: {name}" for name in required if not (root / name).is_file()]
```

Add heading, relative-link, example-shape, declared-variable, and unfinished-marker checks in later tasks. The CLI accepts `--root`, defaults to `docs/study-site-factory`, prints every error, and exits `1` on errors or prints `Validated study-site factory kit.` and exits `0` when clean.

- [ ] **Step 4: Create the project configuration example**

Create valid UTF-8 JSON with these top-level keys and concrete example values:

```json
{
  "version": 1,
  "project": {
    "title": "Network Fundamentals Study",
    "shortTitle": "Network Study",
    "slug": "network-fundamentals-study",
    "description": "A source-backed study and exam website.",
    "brandInitials": "NF",
    "sourceLanguage": "en",
    "studyLanguage": "ar"
  },
  "contentPolicy": {
    "mode": "source-plus-generated",
    "allowOutsideSources": false,
    "generatedQuestionsRequireHumanReviewForExam": true
  },
  "questionGeneration": {
    "mcqPerLesson": 6,
    "trueFalsePerLesson": 4,
    "difficultyPercent": {"easy": 30, "medium": 50, "hard": 20},
    "bloomPercent": {"remember": 25, "apply": 50, "analyze": 25}
  },
  "exam": {"defaultCount": 25, "defaultMinutes": 30},
  "deployment": {
    "provider": "github-pages",
    "repository": "OWNER/REPOSITORY",
    "branch": "master",
    "publicUrl": "https://OWNER.github.io/REPOSITORY/"
  }
}
```

- [ ] **Step 5: Write the foundation documents**

`README.md` must contain `Purpose`, `Use this kit when`, `Do not use it for`, `Reading order`, `Fixed system`, `Configurable inputs`, `Official versus generated content`, and `Validation`.

`00-QUICK-START.md` must contain an exact seven-step flow: copy kit, add materials, complete input, edit config, run the master prompt, review gate reports, deploy only after approval. Include the validator command:

```powershell
python -B scripts/validate_factory_kit.py
```

`01-PROJECT-INPUT-TEMPLATE.md` must contain a copy-ready form and a variable dictionary table declaring at least:

```text
PROJECT_TITLE
PROJECT_SHORT_TITLE
PROJECT_SLUG
PROJECT_DESCRIPTION
BRAND_INITIALS
SOURCE_LANGUAGE
STUDY_LANGUAGE
CONTENT_POLICY
ALLOW_OUTSIDE_SOURCES
MCQ_PER_LESSON
TRUE_FALSE_PER_LESSON
GENERATED_EXAM_REVIEW_POLICY
DEFAULT_EXAM_COUNT
DEFAULT_EXAM_MINUTES
GITHUB_REPOSITORY
GITHUB_BRANCH
PUBLIC_URL
```

The form must make `source-only`, `source-plus-generated`, and `generated-only` mutually exclusive choices and must define what the user supplies when an official answer key is missing.

- [ ] **Step 6: Run focused tests and JSON validation**

Run:

```powershell
python -B -m unittest scripts.test_validate_factory_kit -v
python -m json.tool docs/study-site-factory/examples/project-config.example.json > $null
git diff --check
```

Expected: all validator unit tests pass, JSON parses, and the diff is clean. Do not run the full kit validator yet because later required files do not exist.

- [ ] **Step 7: Commit the foundation**

```powershell
git add scripts/validate_factory_kit.py scripts/test_validate_factory_kit.py docs/study-site-factory/README.md docs/study-site-factory/00-QUICK-START.md docs/study-site-factory/01-PROJECT-INPUT-TEMPLATE.md docs/study-site-factory/examples/project-config.example.json
git commit -m "docs: add study site factory foundation"
```

---

### Task 2: Define the stable product and UX system

**Files:**
- Create: `docs/study-site-factory/02-PRD-TEMPLATE.md`
- Create: `docs/study-site-factory/07-UX-AND-SYSTEM-FLOW.md`
- Modify: `scripts/test_validate_factory_kit.py`

**Interfaces:**
- Consumes: variables declared in `01-PROJECT-INPUT-TEMPLATE.md` and the fixed/configurable boundaries from the design spec.
- Produces: the product contract used by the build workflow and master prompt, plus a stable route and interaction contract used by QA.

- [ ] **Step 1: Add failing product-document tests**

Add these production-file tests as methods on
`FactoryKitValidatorTests`:

```python
from scripts.validate_factory_kit import validate_markdown_headings


    def test_prd_contains_complete_product_contract(self):
        path = Path("docs/study-site-factory/02-PRD-TEMPLATE.md")
        errors = validate_markdown_headings(path, (
            "Product Goal",
            "Users and Jobs",
            "Content Modes",
            "Functional Requirements",
            "Material Requirements",
            "Question Requirements",
            "Persistence",
            "Non-Functional Requirements",
            "Acceptance Criteria",
        ))
        self.assertEqual(errors, [])

    def test_ux_document_contains_every_route(self):
        path = Path("docs/study-site-factory/07-UX-AND-SYSTEM-FLOW.md")
        text = path.read_text(encoding="utf-8")
        routes = (
            "Dashboard", "Material", "Practice", "Mock Exam",
            "Question Bank", "Question Explanations", "Revision Summary",
            "Mistakes", "Bookmarks",
        )
        for route in routes:
            self.assertIn(route, text)
```

- [ ] **Step 2: Run focused tests and verify RED**

Run:

```powershell
python -B -m unittest scripts.test_validate_factory_kit -v
```

Expected: failures because both documents and `validate_markdown_headings` are missing.

- [ ] **Step 3: Implement heading validation**

Add:

```python
def validate_markdown_headings(path: Path, required: tuple[str, ...]) -> list[str]:
    try:
        headings = {
            line.lstrip("#").strip()
            for line in path.read_text(encoding="utf-8").splitlines()
            if line.startswith("#")
        }
    except OSError as error:
        return [f"{path}: cannot read Markdown: {error}"]
    return [f"{path}: missing heading: {heading}" for heading in required if heading not in headings]
```

- [ ] **Step 4: Write the reusable PRD template**

The PRD must separate `Project Variables` from `Fixed Product Requirements`.
It must specify:

- Student and maintainer jobs.
- Source-only, source-plus-generated, and generated-only modes.
- Dashboard metrics using unique and scoreable totals separately.
- Material index and lesson pages.
- Official/generated/mixed Practice pools.
- Mock Exam feedback exclusion and review-item exclusion.
- Question Bank, Question Explanations, Revision, Mistakes, and Bookmarks.
- Versioned LocalStorage, import/export/reset, and legacy normalization.
- LTR/RTL, dark mode, mobile, accessibility, security, and static-hosting rules.
- Measurable acceptance criteria rather than subjective completion language.

Include a `Project-specific decisions` table that uses only variables declared in Task 1.

- [ ] **Step 5: Write the UX and system-flow contract**

Include:

```text
Dashboard -> Material -> Lesson -> linked Practice
Dashboard -> Practice setup -> question -> feedback -> results
Dashboard -> Mock Exam setup -> active exam -> submit -> answer review
Question Bank -> opened question -> marked/source answer -> generated guidance
Material lesson -> linked official/generated questions
Revision/Mistakes/Bookmarks -> focused Practice
```

Define desktop navigation order, mobile primary navigation plus More menu,
route-level empty/error/loading states, 44px minimum touch targets, visible
focus, semantic headings, `lang`/`dir` boundaries, no active-exam explanation
leakage, and labels for `Official source content`, `Generated study guidance`,
`Generated practice question`, and `Needs review — unscored`.

- [ ] **Step 6: Run focused tests and commit**

```powershell
python -B -m unittest scripts.test_validate_factory_kit -v
git diff --check
git add docs/study-site-factory/02-PRD-TEMPLATE.md docs/study-site-factory/07-UX-AND-SYSTEM-FLOW.md scripts/validate_factory_kit.py scripts/test_validate_factory_kit.py
git commit -m "docs: define reusable study product flow"
```

Expected: focused tests pass and only Task 2 files are committed.

---

### Task 3: Define source ingestion and canonical data contracts

**Files:**
- Create: `docs/study-site-factory/03-SOURCE-INGESTION-SPEC.md`
- Create: `docs/study-site-factory/04-CONTENT-AND-DATA-CONTRACTS.md`
- Create: `docs/study-site-factory/examples/source-manifest.example.json`
- Create: `docs/study-site-factory/examples/official-question.example.json`
- Modify: `scripts/validate_factory_kit.py`
- Modify: `scripts/test_validate_factory_kit.py`

**Interfaces:**
- Consumes: configured material files and content policy.
- Produces: `sourceRef`, `sourceManifest`, and `officialQuestion` contracts used by lessons, explanations, generated questions, builders, and QA.

- [ ] **Step 1: Add failing example-shape tests**

Add a validator mapping, then add the test method to
`FactoryKitValidatorTests`:

```python
EXAMPLE_REQUIRED_KEYS = {
    "examples/source-manifest.example.json": {"version", "sources"},
    "examples/official-question.example.json": {
        "id", "origin", "type", "prompt", "topic", "correctAnswer",
        "sourceRefs", "needsReview", "reviewNotes"
    },
}


    def test_source_and_official_question_examples_have_required_keys(self):
        root = Path("docs/study-site-factory")
        for relative, required in EXAMPLE_REQUIRED_KEYS.items():
            payload = json.loads(
                (root / relative).read_text(encoding="utf-8")
            )
            self.assertTrue(required.issubset(payload))
```

- [ ] **Step 2: Run focused tests and verify RED**

Run:

```powershell
python -B -m unittest scripts.test_validate_factory_kit -v
```

Expected: missing example-file failures.

- [ ] **Step 3: Write the source-ingestion specification**

Define exact handling for PDF, DOCX, PPTX, text/Markdown, CSV/JSON, and images.
For every format specify inventory, extraction, visual rendering, provenance,
confidence, and failure behavior. Include this source lifecycle:

```text
inventoried -> extracted -> visually-checked -> normalized -> accepted
                                      `-> needs-review
```

Require `SOURCE_AUDIT_REPORT.md` to record source counts, page/slide counts,
unreadable locations, OCR corrections, duplicate groups, answer-key presence,
and review items. Explicitly forbid silent skipping and answer inference.

- [ ] **Step 4: Write the complete data-contract document**

Define tables for:

- Project configuration.
- Source manifest and `sourceRef`.
- Module, objective, and lesson.
- Official and generated question types.
- Question explanation.
- Review state.
- Versioned LocalStorage progress.
- Session and result records.

For official questions, define type-specific answers for `mcq`, `true-false`,
`true-false-group`, `multi-select`, `matching`, and `ordering`. Require exact
field sets, stable prefixes (`source-`, `module-`, `objective-`, `lesson-`,
`q-`, `gq-`), unique IDs, source references, and strict review/scoring rules.

- [ ] **Step 5: Create valid source and official-question examples**

The source manifest must demonstrate a PDF page and a slide location. The
official question example must be a complete four-option MCQ with:

```json
{
  "id": "q-001",
  "origin": "official",
  "type": "mcq",
  "prompt": "Which protocol automatically assigns IP configuration?",
  "topic": "Networking",
  "options": ["DNS", "DHCP", "HTTP", "SSH"],
  "correctAnswer": 1,
  "sourceRefs": [
    {"sourceId": "source-01", "locationType": "page", "location": 12}
  ],
  "duplicateSources": [],
  "officialExplanation": "",
  "needsReview": false,
  "reviewNotes": ""
}
```

- [ ] **Step 6: Add recursive example validation**

Extend `validate_kit` so it parses every required example and reports missing
top-level keys using `EXAMPLE_REQUIRED_KEYS`. Add source-reference validation:
`sourceId`, `locationType`, and `location` are required; `locationType` must be
one of `page`, `slide`, `section`, `row`, or `image`.

- [ ] **Step 7: Run tests and commit**

```powershell
python -B -m unittest scripts.test_validate_factory_kit -v
python -m json.tool docs/study-site-factory/examples/source-manifest.example.json > $null
python -m json.tool docs/study-site-factory/examples/official-question.example.json > $null
git diff --check
git add docs/study-site-factory/03-SOURCE-INGESTION-SPEC.md docs/study-site-factory/04-CONTENT-AND-DATA-CONTRACTS.md docs/study-site-factory/examples/source-manifest.example.json docs/study-site-factory/examples/official-question.example.json scripts/validate_factory_kit.py scripts/test_validate_factory_kit.py
git commit -m "docs: specify source and content contracts"
```

---

### Task 4: Define Material lessons and generated exam questions

**Files:**
- Create: `docs/study-site-factory/05-MATERIAL-LESSONS-SPEC.md`
- Create: `docs/study-site-factory/06-QUESTION-GENERATION-SPEC.md`
- Create: `docs/study-site-factory/examples/lesson.example.json`
- Create: `docs/study-site-factory/examples/generated-question.example.json`
- Create: `docs/study-site-factory/examples/explanation.example.json`
- Modify: `scripts/validate_factory_kit.py`
- Modify: `scripts/test_validate_factory_kit.py`

**Interfaces:**
- Consumes: source references, module/objective IDs, study language, content policy, and generation quotas.
- Produces: lesson, generated-question, and question-explanation records used by the Material, Practice, Mock Exam, Question Bank, and Question Explanations routes.

- [ ] **Step 1: Add failing lesson and generated-question contract tests**

Add required-key mappings:

```python
EXAMPLE_REQUIRED_KEYS.update({
    "examples/lesson.example.json": {
        "id", "moduleId", "title", "learningObjectives", "summary",
        "explanation", "keyTerms", "workedExamples", "commonMistakes",
        "examTips", "recap", "sourceRefs", "review"
    },
    "examples/generated-question.example.json": {
        "id", "origin", "type", "prompt", "options", "correctAnswer",
        "rationale", "distractorRationales", "difficulty", "bloomLevel",
        "learningObjectiveId", "sourceRefs", "review"
    },
    "examples/explanation.example.json": {
        "questionId", "language", "generatedStudyGuidance", "translation",
        "explanation", "note", "sourceRefs", "review"
    },
})
```

Also assert the generated MCQ has exactly four options, four distractor-rationale
slots, one valid numeric answer index, `origin == "generated"`, and at least one
source reference.

- [ ] **Step 2: Run focused tests and verify RED**

```powershell
python -B -m unittest scripts.test_validate_factory_kit -v
```

Expected: failures for the three missing example files.

- [ ] **Step 3: Write the Material lesson specification**

Define module map, learning objectives, lesson index, lesson page, reading
progress, bookmarks, search, filters, and linked questions. Specify authoring
limits:

- Summary: one short paragraph.
- Explanation: two to five focused paragraphs.
- Every key term has a definition.
- Examples and common mistakes appear only when supported.
- At least one source reference per lesson.
- Recap contains three to seven concise points.
- Empty arrays are allowed only when the source cannot support that content,
  and the coverage report must record the omission.

Include lesson quality checks for coverage, unsupported claims, duplication,
translation, LTR/RTL, readability, source references, and linked-question IDs.

- [ ] **Step 4: Write the generated-question specification**

Include the exact defaults: six MCQs and four True/False items per sufficiently
supported lesson; 30/50/20 difficulty; 25/50/25 remember/apply/analyze; balanced
True/False answers. Define quota shortfall reporting.

Include two complete rubrics:

- MCQ: four options, one answer, one objective, plausible distractors, no answer
  cues, no unsupported facts, rationale plus distractor rationales.
- True/False: one proposition, no double negative, no trivial word-flip, careful
  absolutes, balanced answers, rationale, and corrected false statement.

Define semantic-duplicate checks, answer ambiguity rejection, review states,
Practice eligibility, Mock Exam eligibility, high-stakes human-review policy,
and prohibited claims such as `official exam question`.

- [ ] **Step 5: Create all three example records**

Use one coherent networking lesson and objective across the examples. The
generated MCQ must ask an application-level DHCP question with four plausible
options and a rationale for each slot. The explanation example must use Arabic
study guidance, two Arabic explanation paragraphs, a short Arabic note, and
`generatedStudyGuidance: true` without describing the text as official.

- [ ] **Step 6: Extend validator checks for generated content**

Require:

- Lesson explanations contain two to five non-empty paragraphs.
- Lesson recap contains three to seven non-empty strings.
- Generated MCQ difficulty is `easy`, `medium`, or `hard`.
- Bloom level is `remember`, `apply`, or `analyze`.
- Review status is one of `draft`, `validated`, `human-reviewed`,
  `needs-review`, or `rejected`.
- Explanation guidance flag is exactly `true` and its explanation has two or
  three non-empty paragraphs.

- [ ] **Step 7: Run tests and commit**

```powershell
python -B -m unittest scripts.test_validate_factory_kit -v
Get-ChildItem docs/study-site-factory/examples/*.json | ForEach-Object { python -m json.tool $_.FullName > $null; if ($LASTEXITCODE) { exit $LASTEXITCODE } }
git diff --check
git add docs/study-site-factory/05-MATERIAL-LESSONS-SPEC.md docs/study-site-factory/06-QUESTION-GENERATION-SPEC.md docs/study-site-factory/examples/lesson.example.json docs/study-site-factory/examples/generated-question.example.json docs/study-site-factory/examples/explanation.example.json scripts/validate_factory_kit.py scripts/test_validate_factory_kit.py
git commit -m "docs: define lessons and generated questions"
```

---

### Task 5: Define the resumable build, QA, and deployment workflow

**Files:**
- Create: `docs/study-site-factory/08-BUILD-WORKFLOW.md`
- Create: `docs/study-site-factory/09-QA-GATES.md`
- Create: `docs/study-site-factory/11-HANDOFF-AND-DEPLOYMENT.md`
- Modify: `scripts/test_validate_factory_kit.py`

**Interfaces:**
- Consumes: all product, source, data, lesson, question, and UX contracts.
- Produces: stage artifacts, a progress ledger contract, blocking QA evidence, maintainer instructions, and the deployment/public-verification contract used by the master prompt.

- [ ] **Step 1: Add failing workflow and gate tests**

Add these methods to `FactoryKitValidatorTests` so they require the eight exact
gate headings and the core stage artifacts:

```python
    def test_qa_document_contains_all_blocking_gates(self):
        path = Path("docs/study-site-factory/09-QA-GATES.md")
        text = path.read_text(encoding="utf-8")
        for gate in (
            "Gate 1: Input Completeness",
            "Gate 2: Extraction and Provenance",
            "Gate 3: Canonical Content",
            "Gate 4: Lessons and Guidance",
            "Gate 5: Generated Questions",
            "Gate 6: Application Safety and Logic",
            "Gate 7: Browser QA",
            "Gate 8: Deployment",
        ):
            self.assertIn(gate, text)

    def test_build_workflow_names_resumable_artifacts(self):
        path = Path("docs/study-site-factory/08-BUILD-WORKFLOW.md")
        text = path.read_text(encoding="utf-8")
        artifacts = (
            "SOURCE_AUDIT_REPORT.md", "CONTENT_COVERAGE_REPORT.md",
            "QUESTION_QUALITY_REPORT.md", "FINAL_QA_REPORT.md",
            "progress-ledger.md",
        )
        for artifact in artifacts:
            self.assertIn(artifact, text)
```

- [ ] **Step 2: Run focused tests and verify RED**

```powershell
python -B -m unittest scripts.test_validate_factory_kit -v
```

Expected: missing workflow, QA, and handoff documents.

- [ ] **Step 3: Write the resumable build workflow**

Define 12 stages with inputs, actions, outputs, gate, and resume condition:

1. Initialize project.
2. Inventory sources.
3. Extract and render sources.
4. Audit provenance and confidence.
5. Build module/objective/lesson map.
6. Author Material lessons.
7. Canonicalize official questions.
8. Generate MCQ and True/False pools.
9. Run independent content review.
10. Build deterministic payloads and integrate the static site.
11. Run automated and browser QA.
12. Handoff, deploy, and verify public output.

Define `progress-ledger.md` entries as:

```text
Stage 4: complete
Inputs: input/materials/course.pdf sha256=<hash>
Outputs: reports/SOURCE_AUDIT_REPORT.md sha256=<hash>
Validation: passed
Open reviews: source-01 page 18
Next stage: 5
```

Require content chunking by module or stable ID range and forbid reprocessing a
completed stage when its input hashes are unchanged.

- [ ] **Step 4: Write the blocking QA gates**

For each gate define prerequisite, exact checks, evidence artifact, pass
condition, and failure action. Include example command families for Python
validators, JSON parsing, JavaScript syntax, Node tests, `git diff --check`, a
local static server, Playwright desktop/mobile checks, GitHub Actions monitoring,
HTTP status checks, and public payload counts.

The browser matrix must cover 1440x1000 and 390x844, light/dark, LTR/RTL,
Material reading, Practice feedback, active-Exam non-leakage, Results, search,
filters, pagination, bookmarks, progress import/export, and zero relevant
console errors.

- [ ] **Step 5: Write handoff and deployment instructions**

Cover:

- Maintainer file map.
- Editing source-derived versus generated content.
- Deterministic rebuild and read-only check commands.
- Review-item correction without guessing.
- Versioned progress migration.
- GitHub Pages workflow behavior and manual dispatch.
- Deployment authorization boundary.
- Public HTML/JSON/browser verification.
- Rollback using a normal Git revert rather than destructive reset.
- Final handoff summary fields: repository, branch, commit, URL, counts, review
  items, tests, workflow run, and known limitations.

- [ ] **Step 6: Run tests and commit**

```powershell
python -B -m unittest scripts.test_validate_factory_kit -v
git diff --check
git add docs/study-site-factory/08-BUILD-WORKFLOW.md docs/study-site-factory/09-QA-GATES.md docs/study-site-factory/11-HANDOFF-AND-DEPLOYMENT.md scripts/test_validate_factory_kit.py
git commit -m "docs: add factory workflow and quality gates"
```

---

### Task 6: Add the master prompt and validate the complete kit

**Files:**
- Create: `docs/study-site-factory/10-MASTER-BUILD-PROMPT.md`
- Modify: `docs/study-site-factory/README.md`
- Modify: `docs/study-site-factory/00-QUICK-START.md`
- Modify: `scripts/validate_factory_kit.py`
- Modify: `scripts/test_validate_factory_kit.py`

**Interfaces:**
- Consumes: every numbered factory document, example, configuration value, stage artifact, and QA gate.
- Produces: one copy-ready project-start prompt and a fully validated documentation kit.

- [ ] **Step 1: Add failing full-kit validation tests**

Add these methods to `FactoryKitValidatorTests` for required files, declared
variables, relative Markdown links, and unfinished markers:

```python
    def test_complete_factory_kit_passes(self):
        root = Path("docs/study-site-factory")
        self.assertEqual(validate_kit(root), [])

    def test_all_template_variables_are_declared(self):
        root = Path("docs/study-site-factory")
        declared = collect_declared_variables(
            root / "01-PROJECT-INPUT-TEMPLATE.md"
        )
        used = set().union(*(
            collect_template_variables(path.read_text(encoding="utf-8"))
            for path in root.glob("*.md")
        ))
        self.assertEqual(used - declared, set())
```

- [ ] **Step 2: Run the full test and verify RED**

```powershell
python -B -m unittest scripts.test_validate_factory_kit -v
```

Expected: missing master prompt and incomplete `validate_kit` checks.

- [ ] **Step 3: Implement complete-kit validation**

Add:

```python
MARKDOWN_LINK = re.compile(r"\[[^\]]+\]\(([^)]+)\)")
UNFINISHED_MARKERS = ("T" + "BD", "T" + "ODO", "implement" + " later", "fill" + " in later")


def collect_declared_variables(path: Path) -> set[str]:
    return collect_template_variables(path.read_text(encoding="utf-8"))


def validate_internal_links(root: Path, markdown_paths: list[Path]) -> list[str]:
    errors = []
    for path in markdown_paths:
        for target in MARKDOWN_LINK.findall(path.read_text(encoding="utf-8")):
            if target.startswith(("http://", "https://", "#")):
                continue
            clean_target = target.split("#", 1)[0]
            if clean_target and not (path.parent / clean_target).resolve().exists():
                errors.append(f"{path}: broken relative link: {target}")
    return errors
```

`validate_kit` must aggregate:

- Required documents and examples.
- JSON parsing and required-key rules.
- Required headings.
- Source-reference enums.
- Generated lesson/question/explanation shape rules.
- Every used template variable declared in `01-PROJECT-INPUT-TEMPLATE.md`.
- Relative Markdown links resolve.
- No unfinished marker appears in delivered factory documents.

- [ ] **Step 4: Write the master build prompt**

Make the prompt copy-ready and imperative. It must instruct the agent to:

1. Read `PROJECT_INPUT.md` and `project-config.json` first.
2. Validate minimum inputs before acting.
3. Read only the numbered document for the active stage plus the shared data
   contracts and QA gate.
4. Keep a progress ledger and content hashes.
5. Use source-appropriate extraction and visual inspection.
6. Separate official, generated, and review content.
7. Build Material lessons and exam-quality MCQ/True-False questions.
8. Stop at unresolved evidence rather than guess.
9. Use the current static study-site repository as the UI implementation base.
10. Run every blocking gate and repair failures.
11. Request deployment authorization if it was not already given.
12. Finish with repository, commit, public URL, counts, review items, and test
    evidence.

Include a `Low-token operating mode` section that requires stage-scoped reads,
stable chunks, artifact reuse, no repeated product explanation, deterministic
builders, and concise status updates.

- [ ] **Step 5: Complete README cross-links and quick-start invocation**

Link every numbered document and JSON example from `README.md`. Add a
`Start a new project` section to `00-QUICK-START.md` with:

```text
Use docs/study-site-factory/10-MASTER-BUILD-PROMPT.md.
Project input: input/PROJECT_INPUT.md
Configuration: input/project-config.json
Materials: input/materials/
```

Every link must be relative and resolve inside the repository.

- [ ] **Step 6: Run complete deterministic validation**

```powershell
python -B -m unittest scripts.test_validate_factory_kit -v
python -B scripts/validate_factory_kit.py
Get-ChildItem docs/study-site-factory/examples/*.json | ForEach-Object { python -m json.tool $_.FullName > $null; if ($LASTEXITCODE) { exit $LASTEXITCODE } }
git diff --check
```

Expected: all tests pass, the validator prints `Validated study-site factory kit.`, all six JSON files parse, and the diff is clean.

- [ ] **Step 7: Perform a token and consistency dry run**

Using the example configuration, verify manually and record in the test report:

- The project can be initialized without reading current ITS-specific content.
- The master prompt names the correct first three inputs.
- Every downstream artifact has a producing stage.
- Every QA gate has a pass condition and failure action.
- Official and generated content cannot share an unlabeled pool.
- Generated questions have evidence, difficulty, objective, rationale, and
  review status.
- Material lessons have every required section.
- Deployment is not authorized implicitly.

- [ ] **Step 8: Commit the completed kit**

```powershell
git add docs/study-site-factory/README.md docs/study-site-factory/00-QUICK-START.md docs/study-site-factory/10-MASTER-BUILD-PROMPT.md scripts/validate_factory_kit.py scripts/test_validate_factory_kit.py
git commit -m "docs: complete reusable study site factory"
```

---

### Task 7: Final independent review and handoff

**Files:**
- Verify: `docs/study-site-factory/`
- Verify: `scripts/validate_factory_kit.py`
- Verify: `scripts/test_validate_factory_kit.py`
- Verify: `docs/superpowers/specs/2026-08-20-study-site-documentation-factory-design.md`

**Interfaces:**
- Consumes: the complete committed kit.
- Produces: a reviewed, ready-to-copy factory with evidence that it satisfies the approved design.

- [ ] **Step 1: Run a specification coverage audit**

Map every acceptance criterion in the design spec to an exact factory file and
section. Record any missing requirement as Critical or Important and fix it
before proceeding.

- [ ] **Step 2: Run a fresh full validation gate**

```powershell
python -B -m unittest scripts.test_validate_factory_kit -v
python -B scripts/validate_factory_kit.py
git diff --check
git status --short
```

Expected: tests and validator pass, no tracked modifications remain, and only
pre-existing user-owned untracked source files may appear.

- [ ] **Step 3: Request an independent documentation review**

Review the complete range from the pre-kit base commit to `HEAD`. Require the
reviewer to check:

- Internal consistency and no contradictory rules.
- Complete template-variable declaration.
- Usability by an agent with no knowledge of the ITS project.
- Official/generated/review data separation.
- Material section completeness.
- MCQ and True/False exam-quality rubrics.
- Resumability and token-efficiency instructions.
- Executable QA evidence and deployment authorization boundaries.
- Valid JSON examples and relative links.

Fix every Critical or Important finding and re-run the scoped review.

- [ ] **Step 4: Provide the final handoff**

Report:

- Factory root: `docs/study-site-factory/`.
- Start file: `00-QUICK-START.md`.
- Copy-ready prompt: `10-MASTER-BUILD-PROMPT.md`.
- Project input template: `01-PROJECT-INPUT-TEMPLATE.md`.
- Validator command and passing test count.
- Commit SHA.
- Any intentionally untracked user source files left unchanged.
