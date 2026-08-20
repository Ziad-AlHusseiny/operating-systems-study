# Study Website Documentation Factory Kit Design

## Goal

Create a reusable documentation factory kit that lets a human or coding agent
turn a new set of learning materials into the same kind of lightweight study
website as the current ITS site, without redesigning the product or rewriting
the operating instructions for every course.

The kit must support repeated use across roughly 20 independent websites. Each
website may use different PDFs, Word documents, slide decks, text files, or
images, but must keep the same product flow, quality boundaries, and simple
technical architecture.

## Chosen Approach

Use a documentation-and-schema factory rather than a single prompt or a custom
CLI generator.

The factory will contain:

- A short project-input form for course-specific decisions.
- A reusable product requirements document.
- Exact content and JSON data contracts.
- Material-ingestion and source-audit rules.
- Material-lesson and question-explanation writing rules.
- Exam-quality MCQ and True/False generation rules.
- A fixed UX and system flow.
- An implementation playbook with resumable stages.
- Automated and browser QA gates.
- A master build prompt that references the kit instead of repeating it.
- Handoff and deployment checklists.

This approach is recommended because it standardizes results while remaining
easy to inspect, edit, and use with different agents or repositories. A future
CLI may automate these documents, but it is not required for this kit.

## Design Principles

1. **Material changes; system stays stable.** Course content, language,
   branding, and question quotas are configuration. Navigation, data
   boundaries, review behavior, testing, and deployment flow are reusable.
2. **Official and generated content never mix silently.** Source questions,
   source answers, generated explanations, and generated questions use separate
   records and visible labels.
3. **Every learning claim is traceable.** Lessons, explanations, and generated
   questions carry source references to a file plus page, slide, section, or
   image identifier.
4. **Uncertainty is preserved, not guessed away.** Missing answers, conflicting
   keys, poor OCR, and unsupported claims become review items and remain
   unscored.
5. **Simple technology is the default.** HTML, CSS, vanilla JavaScript, JSON,
   and LocalStorage remain sufficient for the default product.
6. **The kit is resumable.** Every stage writes an artifact and a validation
   report, so a later session can continue without rereading all source files.
7. **Quality gates are executable.** A site is not complete because content was
   generated; it is complete only after schemas, evidence, scoring, browser
   flows, responsiveness, and deployment have passed.

## Supported Inputs

The factory accepts:

- Searchable or image-based PDF files.
- DOCX and other Word-compatible documents.
- PPTX and other slide-deck formats.
- Plain text, Markdown, CSV, and JSON files.
- Page or slide images.
- Optional answer keys, syllabi, learning objectives, and instructor notes.

The minimum project package contains:

1. One completed project-input file.
2. One project configuration JSON file.
3. At least one source material.
4. A declared source policy: source-only, source-plus-generated, or
   generated-only.

If answer keys are absent, the system may generate practice questions from the
material, but it must not label an inferred answer as an official source answer.

## Factory Kit Structure

Create the kit at `docs/study-site-factory/`:

```text
docs/study-site-factory/
|-- README.md
|-- 00-QUICK-START.md
|-- 01-PROJECT-INPUT-TEMPLATE.md
|-- 02-PRD-TEMPLATE.md
|-- 03-SOURCE-INGESTION-SPEC.md
|-- 04-CONTENT-AND-DATA-CONTRACTS.md
|-- 05-MATERIAL-LESSONS-SPEC.md
|-- 06-QUESTION-GENERATION-SPEC.md
|-- 07-UX-AND-SYSTEM-FLOW.md
|-- 08-BUILD-WORKFLOW.md
|-- 09-QA-GATES.md
|-- 10-MASTER-BUILD-PROMPT.md
|-- 11-HANDOFF-AND-DEPLOYMENT.md
`-- examples/
    |-- project-config.example.json
    |-- source-manifest.example.json
    |-- lesson.example.json
    |-- official-question.example.json
    |-- generated-question.example.json
    `-- explanation.example.json
```

The numbered filenames define the reading order. The master prompt must tell an
agent to read the project input and configuration first, then only the factory
documents needed for the current stage.

## Template Variable Convention

Reusable documents use uppercase double-brace variables, for example:

```text
{{PROJECT_TITLE}}
{{PROJECT_SLUG}}
{{SOURCE_LANGUAGE}}
{{STUDY_LANGUAGE}}
{{TARGET_MCQ_COUNT}}
{{TARGET_TRUE_FALSE_COUNT}}
{{GITHUB_REPOSITORY}}
```

These tokens are intentional template variables, not unfinished requirements.
Every variable used by the kit must be defined in the project-input template or
the project configuration example. No free-form `TBD` or undocumented token is
allowed.

## Configuration Boundaries

### Configurable Per Website

- Course title, short title, slug, and description.
- Brand initials and restrained color tokens.
- Source and study languages.
- Source collections and labels.
- Enabled question types.
- Generated-question counts and difficulty distribution.
- Whether generated questions require human review before Mock Exam use.
- Timer and default practice/exam counts.
- GitHub repository and public URL.

### Fixed Unless the Product Itself Changes

- Static application architecture.
- Separation of official and generated data.
- Stable IDs and source references.
- Review items are unscored and excluded from Mock Exams.
- Search, filters, Practice, Mock Exam, Revision, Mistakes, Bookmarks, results,
  and progress import/export.
- Material lessons and question explanations remain distinct sections.
- Safe HTML escaping, strict schema validation, accessibility rules, mobile
  behavior, test gates, and deployment verification.

## Standard Project Output

Each generated project should follow this logical structure:

```text
input/
|-- PROJECT_INPUT.md
|-- project-config.json
`-- materials/
content/
|-- source-manifest.json
|-- lessons/
|-- official-questions/
|-- generated-questions/
`-- explanations/
scripts/
reports/
|-- SOURCE_AUDIT_REPORT.md
|-- CONTENT_COVERAGE_REPORT.md
|-- QUESTION_QUALITY_REPORT.md
`-- FINAL_QA_REPORT.md
study-website/
|-- index.html
|-- css/
|-- js/
|-- data/
|-- assets/
|-- tests/
`-- README.md
```

The final static delivery folder must not require the original source files,
temporary OCR output, Python packages, Node packages, or a build step.

## End-to-End Factory Flow

```text
Project input and configuration
-> source inventory and rendering
-> extraction with page/slide provenance
-> source audit and confidence review
-> topic, module, lesson, and objective map
-> material explanations and revision summaries
-> official-question canonicalization
-> generated MCQ and True/False authoring
-> independent evidence and quality validation
-> deterministic JSON payloads
-> static website integration
-> automated tests
-> desktop/mobile browser QA
-> deployment and public verification
```

Every arrow is a gate. A failed stage must be repaired before downstream
content is treated as final.

## Content Boundaries

### Source Material

Source text is extracted or carefully normalized from supplied files. It keeps
file, page, slide, section, or image provenance. Obvious OCR corrections may be
made only when the visible source supports them.

### Official Questions

Official questions and marked answers remain faithful to supplied sources.
Duplicate questions may be merged, but every original reference must be kept.
Conflicting, incomplete, or conceptually contradictory keys use
`needsReview: true`, remain visible for study, stay unscored, and are excluded
from Mock Exams.

### Generated Material Guidance

Lesson explanations, translations, examples, common mistakes, exam tips, and
revision notes are generated study guidance. They live separately from source
records and are visibly labeled as generated.

### Generated Questions

Generated MCQ and True/False questions use a dedicated pool. They must never be
described as official source questions. The UI and configuration must let users
choose official, generated, or mixed Practice pools. Generated questions enter
Mock Exams only after the configured review gate passes.

## Core Data Contracts

The full JSON examples and field tables will live in
`04-CONTENT-AND-DATA-CONTRACTS.md`. The design requires these record families.

### Source Reference

```json
{
  "sourceId": "source-01",
  "file": "course-material.pdf",
  "locationType": "page",
  "location": 12,
  "section": "Network permissions"
}
```

`locationType` supports `page`, `slide`, `section`, `row`, or `image`.

### Lesson Record

```json
{
  "id": "lesson-network-permissions",
  "moduleId": "module-networking",
  "title": "Network permissions",
  "learningObjectives": ["Determine effective file permissions"],
  "summary": "A short revision summary.",
  "explanation": ["Concept paragraph one.", "Concept paragraph two."],
  "keyTerms": [{"term": "NTFS", "definition": "Definition."}],
  "workedExamples": ["One evidence-based example."],
  "commonMistakes": ["One common misunderstanding."],
  "examTips": ["One concise exam cue."],
  "recap": ["One key point."],
  "sourceRefs": [{"sourceId": "source-01", "locationType": "page", "location": 12}],
  "review": {"status": "validated", "notes": ""}
}
```

### Official Question Record

An official question uses a stable `q-` ID, `origin: "official"`, its complete
type-specific content, exact source references, marked answer, duplicate
sources, and review state. Its answer is never silently replaced by generated
reasoning.

### Generated Question Record

```json
{
  "id": "gq-network-permissions-001",
  "origin": "generated",
  "type": "mcq",
  "prompt": "A clear exam-style prompt.",
  "options": ["Option A", "Option B", "Option C", "Option D"],
  "correctAnswer": 1,
  "rationale": "Why the supported answer is correct.",
  "distractorRationales": ["Why A is wrong", "", "Why C is wrong", "Why D is wrong"],
  "difficulty": "medium",
  "bloomLevel": "apply",
  "learningObjectiveId": "objective-network-permissions-01",
  "sourceRefs": [{"sourceId": "source-01", "locationType": "page", "location": 12}],
  "review": {"status": "validated", "notes": ""}
}
```

Generated True/False records replace `options` and the numeric answer with a
single testable statement and a Boolean answer. Every generated record includes
an evidence-based rationale.

### Question Explanation Record

Question explanations are keyed by question ID and contain a complete study-
language translation when needed, two or three short explanation paragraphs,
and a concise revision note. They remain separate from both official and
generated question records.

## Material Explanation Section

The website gains a primary route named `Material` or a configured equivalent.

### Material Index

- Course overview and coverage count.
- Module and lesson navigation.
- Search across titles, summaries, explanations, terms, and exam tips.
- Filters by module, topic, source, and completion state.
- Resume-last-lesson action.

### Lesson Page

Each lesson presents:

1. Title and learning objectives.
2. Short revision summary.
3. Two to five clear explanation paragraphs.
4. Key terms and definitions.
5. Evidence-based worked examples where the material supports them.
6. Common mistakes or misconceptions.
7. Exam-focused tips.
8. A final recap.
9. Source references.
10. Linked official and generated practice questions.

The section must support LTR and RTL study languages, dark mode, mobile reading,
bookmarks, and LocalStorage lesson progress.

## Exam-Quality Question Generation

### Default Distribution

Unless overridden in project configuration:

- Generate six MCQs and four True/False questions per lesson with enough
  material.
- Difficulty: 30 percent easy, 50 percent medium, 20 percent hard.
- Cognitive level: 25 percent remember, 50 percent apply, 25 percent analyze.
- Keep True and False answers balanced across the full generated pool.

If a lesson cannot support its quota without repetition or unsupported claims,
generate fewer questions and report the shortfall.

### MCQ Rules

- Exactly four options and one defensible correct answer by default.
- Prompt tests one learning objective.
- Distractors are plausible misconceptions supported by nearby concepts.
- Avoid length, grammar, capitalization, or repetition clues.
- Avoid `All of the above` and `None of the above` unless explicitly enabled.
- Avoid trick wording and unnecessary negatives.
- Explain the correct option and every distractor.
- Do not depend on facts absent from the supplied material unless the project
  explicitly permits outside authoritative sources.

### True/False Rules

- Test one proposition only.
- Avoid vague qualifiers and accidental double negatives.
- Avoid making an item false through one trivial changed word.
- Use absolute words only when the source itself supports an absolute claim.
- Provide a rationale and a corrected statement for false items.

### Generated-Question Review States

- `draft`: not displayed.
- `validated`: passed schema, evidence, ambiguity, duplication, and answer
  checks; available in Practice.
- `human-reviewed`: approved for Mock Exam when human review is required.
- `needs-review`: visible only in review tools and never scored.
- `rejected`: excluded from delivered payloads.

## Standard Website Flow

Desktop navigation uses this stable model:

1. Dashboard
2. Material
3. Practice
4. Mock Exam
5. Question Bank
6. Question Explanations
7. Revision Summary
8. Mistakes
9. Bookmarks

Mobile uses a bottom navigation for primary actions and an accessible More menu
for secondary routes.

### Practice

Users choose material scope, topic, question origin, type, status, count, and
order. Feedback appears after checking an answer and may show the rationale,
question explanation, source references, and review warning.

### Mock Exam

Users choose official, generated, or mixed validated pools, count, and timer.
No answer feedback or explanation appears before submission. Review items never
enter the exam. Results show scoreable totals, skipped items, performance by
topic/source/origin, and complete post-submission review.

### Persistence

LocalStorage saves question progress, lesson progress, bookmarks, theme,
sessions, and results in a versioned schema. Imported or legacy progress is
normalized against the current content and review flags before use.

## Quality Gates

### Gate 1: Input Completeness

- Project input and configuration validate.
- Every supplied file appears in the source manifest.
- Password-protected, corrupt, or unsupported files are reported.

### Gate 2: Extraction and Provenance

- Page/slide totals and extracted coverage are recorded.
- Image-based pages are rendered and inspected.
- Low-confidence OCR is flagged.
- Every content record has a valid source reference.

### Gate 3: Canonical Content

- Stable IDs are unique.
- Duplicate sources are preserved.
- Official answers match visible marks.
- Conflicts and contradictions are review-only and unscored.

### Gate 4: Lessons and Guidance

- Lesson coverage maps to the material inventory.
- Generated statements are supported by source references.
- Translation and study-language rules pass.
- Empty, duplicated, or excessively long sections fail validation.

### Gate 5: Generated Questions

- Target coverage and reported shortfalls are explicit.
- Every answer and rationale is evidence-backed.
- MCQ distractors and True/False wording pass their rubrics.
- Semantic duplicates, ambiguous answers, and leakage from the answer wording
  are rejected.

### Gate 6: Application Safety and Logic

- JSON schemas and exact ID coverage pass.
- All rendered content is escaped.
- Scoring, shuffling, filters, persistence, import/export, review items, and
  legacy-state normalization pass automated tests.

### Gate 7: Browser QA

- Desktop and mobile layouts pass with no horizontal overflow.
- Light/dark themes, keyboard focus, RTL/LTR direction, touch targets, and
  contrast pass.
- Material, Practice, active Exam, Results, Question Bank, explanations,
  bookmarks, and progress flows pass with zero relevant console errors.

### Gate 8: Deployment

- Static hosting workflow succeeds.
- Public HTML and every required JSON payload return HTTP 200.
- Public browser smoke tests confirm the expected content counts and routes.

## Token-Efficiency Strategy

The kit saves tokens through process, not through weaker validation:

- Put all reusable requirements in the factory documents once.
- Keep the per-project input short and configuration-driven.
- Use one master prompt that references files rather than repeating them.
- Inventory sources once, then process them in stable chunks.
- Save extracted text, manifests, canonical records, and review reports between
  sessions.
- Generate lessons and questions by module or ID range.
- Give each agent only the relevant source chunk, schema, and task brief.
- Use deterministic builders so generated delivery files never require manual
  rewriting.
- Use `--check` modes to compare committed artifacts without modifying them.
- Resume from a progress ledger instead of restating completed work.

## Error and Review Policy

- Do not silently skip unreadable pages or slides.
- Do not infer official answers from generated explanations.
- Do not use outside information unless the project configuration permits it
  and the source type is recorded.
- Do not make a question scoreable if its evidence is incomplete or ambiguous.
- Preserve source contradictions with exact references.
- Show generated-content and review labels in both data and UI.
- A material-load failure must not corrupt saved progress.
- Optional generated guidance may fail softly without disabling official
  question modes.

## Documentation Responsibilities

The factory kit must explain both human and agent responsibilities:

- The human supplies materials, configuration, deployment destination, and any
  required approval decisions.
- The agent inventories and validates inputs, produces traceable content,
  implements the fixed site flow, runs gates, and reports unresolved items.
- Neither party treats generated content as official source content.

## Non-Goals

- No backend, account system, live collaboration, payment, or analytics
  platform.
- No automatic publishing without explicit project authorization.
- No guarantee that poor or incomplete material can support a requested number
  of high-quality questions.
- No claim that generated questions are official exam questions.
- No replacement for expert review in regulated or high-stakes subjects.
- No full CLI scaffolder in this version of the factory.

## Acceptance Criteria

The documentation factory kit is complete when:

- Every file in the declared kit structure exists and has one clear purpose.
- A new project can be specified using only the input template, configuration,
  and source files.
- Every template variable is documented and used consistently.
- The PRD describes the complete current website flow plus the Material section.
- Data contracts separate source, official, generated, explanation, and progress
  content.
- Generated MCQ and True/False rules are detailed enough for independent
  authoring and review.
- The workflow is resumable and includes explicit artifacts at every stage.
- QA gates cover source evidence, content quality, application behavior,
  accessibility, browser flows, and public deployment.
- The master prompt can start a new project without repeating the full product
  specification in chat.
- JSON examples parse successfully.
- Markdown links and referenced paths are valid.
- A self-review finds no undocumented placeholders, contradictory rules, or
  missing system-flow sections.

