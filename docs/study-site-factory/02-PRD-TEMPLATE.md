# Product requirements document template

Use this document to define the stable study-site product for one new project.
Complete the project variables from
[01-PROJECT-INPUT-TEMPLATE.md](01-PROJECT-INPUT-TEMPLATE.md); do not add a
project-specific feature or policy outside that input contract.

## Project Variables

| Decision | Variable | Product use |
| --- | --- | --- |
| Site identity | `{{PROJECT_TITLE}}`, `{{PROJECT_SHORT_TITLE}}`, `{{PROJECT_SLUG}}`, `{{PROJECT_DESCRIPTION}}`, `{{BRAND_INITIALS}}` | Browser title, branding, routes, and source-backed description. |
| Language direction | `{{SOURCE_LANGUAGE}}`, `{{STUDY_LANGUAGE}}` | Source display, learner-facing language, and document direction. |
| Content boundaries | `{{CONTENT_POLICY}}`, `{{ALLOW_OUTSIDE_SOURCES}}` | Permitted content mode and whether approved outside authorities may supplement declared materials. |
| Practice volume | `{{MCQ_PER_LESSON}}`, `{{TRUE_FALSE_PER_LESSON}}` | Target generated practice volume for each sufficiently supported lesson. |
| Exam safety | `{{GENERATED_EXAM_REVIEW_POLICY}}`, `{{DEFAULT_EXAM_COUNT}}`, `{{DEFAULT_EXAM_MINUTES}}` | Generated-question approval gate plus default Mock Exam count and time. |
| Publication | `{{GITHUB_REPOSITORY}}`, `{{GITHUB_BRANCH}}`, `{{PUBLIC_URL}}` | Static deployment destination and public verification target. |

## Fixed Product Requirements

The product is a static, source-backed study and exam website. It has no
accounts, backend, database, or unstated authority. Official source content,
generated study guidance, generated practice questions, and review-only items
are separate records and must never appear as one unlabeled pool.

## Product Goal

Help a learner move from traceable course material to focused practice and
measurable revision while preserving the source, confidence, and scoring state
of every item. The site must remain useful after a refresh through local,
versioned progress data and must be deployable to static hosting.

## Users and Jobs

| User | Job to be done |
| --- | --- |
| Student | Find a lesson, understand its source-backed content, practise a chosen topic, sit a timed Mock Exam, and return to mistakes or saved items. |
| Content maintainer | Add or correct source-derived records, retain provenance, review generated material, publish static data, and resolve uncertain items without inventing answers. |

## Content Modes

The selected `{{CONTENT_POLICY}}` is exactly one of these modes:

| Mode | Allowed learner content |
| --- | --- |
| `source-only` | Supplied material and official source questions; no generated guidance or generated questions. |
| `source-plus-generated` | Source and official content plus separately labeled generated guidance and generated questions supported by source references. |
| `generated-only` | Generated study content and questions supported by declared materials; it must not be represented as official source content. |

Only approved authorities may be used when `{{ALLOW_OUTSIDE_SOURCES}}` permits
them. Unsupported, contradictory, or uncertain claims remain review-only and
unscored.

## Functional Requirements

- Dashboard shows separate unique totals for lessons, available questions,
  mistakes, and bookmarks; scoreable totals count only items with approved
  answers, while unique totals count each stable item once.
- Dashboard offers clear entry points to Material, Practice, Mock Exam,
  Question Bank, Revision Summary, Mistakes, and Bookmarks.
- A Material index supports module or lesson discovery, progress indication,
  search, and filters. A lesson page provides its objectives, source-backed
  explanation, source references, and linked questions.
- Practice lets the learner choose scope and pool: official, generated, or
  mixed when the selected content mode permits it. Feedback follows the answer
  submission and identifies the content origin.
- Mock Exam uses a fixed question set and timer after setup. It excludes
  feedback, explanations, correct-answer indicators, and generated guidance
  during the active exam. Results and answer review are available only after
  submission or expiry.
- Question Bank supports browsing and filtering questions by topic, type,
  origin, and scoring status. Question Explanations shows the marked/source
  answer separately from generated guidance.
- Revision Summary summarizes scoreable performance and coverage without
  treating review-only items as correct or incorrect. Mistakes and Bookmarks
  each start focused Practice using their respective set.

## Material Requirements

- The Material index lists every available module and lesson with a stable ID,
  title, progress state, and source coverage state.
- Each lesson links only to questions that cite supporting source references.
- A lesson displays source-derived material separately from any `Generated
  study guidance`; generated text never replaces a source reference.
- Empty lessons, unavailable source media, and unresolved source mapping show
  a route-level state instead of fabricated content.

## Question Requirements

- Official pools contain only faithful source questions and approved marked
  answers. Generated pools contain only questions labeled `Generated practice
  question` with provenance and review state.
- A mixed Practice pool identifies every item’s origin before submission.
- Items marked `Needs review — unscored` never affect scoreable totals or
  scores. They cannot enter an official Mock Exam question set.
- Generated questions may enter Mock Exam only when they satisfy
  `{{GENERATED_EXAM_REVIEW_POLICY}}`; otherwise they remain Practice-only.
- Missing official answers remain visibly unscored. Maintainers must correct
  them from an approved answer key or keep them review-only.

## Persistence

- Store learner progress in versioned LocalStorage under a project-specific
  key derived from `{{PROJECT_SLUG}}`.
- Persist lesson progress, attempts, scoreable results, mistakes, bookmarks,
  preferences, and resumable active-exam state only on the learner device.
- Provide export, import, and reset controls. Import validates the version and
  data shape before replacing existing data; reset requires confirmation.
- Normalize supported legacy records during loading, preserve valid data where
  possible, and report incompatible records rather than silently mis-scoring
  them.

## Non-Functional Requirements

- Support LTR and RTL presentation according to `{{STUDY_LANGUAGE}}`; set
  document `lang` and `dir` explicitly and isolate differently directed source
  excerpts.
- Provide dark mode, responsive mobile layouts, keyboard operation, visible
  focus, semantic headings, sufficient contrast, and 44px minimum touch
  targets for interactive controls.
- Escape untrusted source data, avoid executing source-derived HTML, make no
  network request necessary for core study use, and expose no secrets in the
  static output.
- Publish as a static site to `{{PUBLIC_URL}}` from
  `{{GITHUB_REPOSITORY}}` on `{{GITHUB_BRANCH}}`.

## Acceptance Criteria

- A learner can reach any listed primary route from desktop navigation and
  mobile navigation in two or fewer navigation actions.
- Dashboard reports a unique total and a scoreable total as distinct values;
  changing a review-only item cannot increase the scoreable total.
- Every lesson has at least one displayed source reference or is explicitly
  shown as unavailable or review-only.
- During an active Mock Exam, no correct answer, rationale, explanation,
  generated guidance, or per-question correctness indicator is rendered.
- A submitted Mock Exam displays a score calculated only from scoreable,
  eligible questions and then permits answer review.
- Imported progress with a supported prior version is normalized before use;
  incompatible data is rejected with a visible message and leaves current data
  unchanged.
- At 390px viewport width, all primary controls remain reachable, usable, and
  at least 44px in their touch dimension; at desktop width, keyboard focus is
  visible on every interactive control.
- Every generated learner-facing item carries its required generated label;
  every unscored item carries `Needs review — unscored`.
