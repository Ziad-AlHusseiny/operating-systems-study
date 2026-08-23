# Material Lessons Specification

## Purpose and Inputs

The Material pipeline turns accepted source references, canonical `module-` and `objective-` IDs, the configured study language, and the content policy into source-grounded lessons. Its records feed Material, Practice, Mock Exam, Question Bank, and Question Explanations without changing the ID, source-reference, review, or scoring rules in `04-CONTENT-AND-DATA-CONTRACTS.md`.

## Canonical Mapping

The lesson authoring record is a readable input to the canonical Lesson and Material Section records. Compilation creates the canonical Lesson by copying `id`, `moduleId`, `objectiveIds`, `title`, `sourceRefs`, `needsReview`, and `reviewNotes` without alteration, then setting canonical `body` to the two-to-five `explanation` paragraphs joined in order with exactly two newline characters (`\n\n`). The authoring record stores that compiled `body` so validation can reject transformation drift. `learningObjectives` must be an ordered array of objective records, and `learningObjectives[].id` must equal `objectiveIds` in both values and order.

Compilation also creates the canonical Material Section with the same learner-facing `title`. It maps `summary` to one canonical `summaries` item, `keyTerms` to `terms`, `workedExamples` to `examples`, `commonMistakes` to `mistakes`, `examTips` to `examTips`, and each `recap` string to a canonical `recaps` item. Every compiled item inherits or narrows the lesson's non-empty `sourceRefs`; it never loses evidence. Missing canonical Lesson fields, a changed title, an objective-order mismatch, or a `body` that is not the exact paragraph join is a validation failure.

`review.status` is an authoring workflow view with the values `draft`, `validated`, `human-reviewed`, `needs-review`, or `rejected`. It does not replace canonical `needsReview`/`reviewNotes` or an immutable Review approval record. A `human-reviewed` item is approved only when its nested approval has canonical `status: completed` and `decision: approved` for the current content version.

## Module Map and Learning Objectives

The module map is ordered by Module `order`. Each card shows the module title, objective count, lesson count, completion, and source-coverage state. Opening a module reveals objectives and its ordered lesson index. IDs are stable: a module uses `module-`, an objective uses `objective-`, and a lesson uses `lesson-`. Every objective belongs to its lesson's module, is observable and assessable, and has at least one valid source reference. A lesson may cover several objectives, but it must not silently introduce an objective from another module.

## Lesson Index

The lesson index provides title, module, objective labels, estimated reading status, completion, bookmark state, source coverage, and linked-question count. The default order follows module order and lesson order. It supports search and filters without changing that canonical order when filters are cleared. A result with unresolved evidence is visibly labelled `Needs review — unscored`.

## Lesson Page

A lesson page renders, in order: title and objectives; one summary; explanation; key terms; supported worked examples; supported common mistakes; supported exam tips; recap; source references; and linked questions. The authoring limits are mandatory:

- Summary is one short paragraph.
- Explanation contains two to five focused, non-empty paragraphs.
- Every key term has a non-empty definition and evidence.
- Worked examples and common mistakes appear only when the accepted source supports them.
- Every lesson has at least one source reference.
- Recap contains three to seven concise, non-empty points.
- Empty `workedExamples`, `commonMistakes`, or `examTips` arrays are allowed only when the source cannot support that content, and the coverage report records the omitted field, lesson ID, checked sources, and reason.

Empty required narrative content is not an acceptable omission. Unsupported content is removed or sent to review, never filled with general knowledge.

## Reading Progress and Bookmarks

Opening a lesson records `lastVisitedAt`; explicit learner actions set `lessonProgress[lessonId].status` to `not-started`, `in-progress`, or `completed`. Scrolling alone does not mark completion. Progress is stored under the versioned LocalStorage contract and survives search or filter changes. A bookmark stores the canonical lesson ID, is idempotent, and appears in both Material and Bookmarks. Removed or unknown IDs are preserved for migration but not rendered as valid lessons.

## Search, Filters, and Linked Questions

Search uses normalized title, objective text, summary, explanation, key terms, and recap in both source and study languages. Filters include module, objective, completion, bookmark, source-coverage state, and review state; filters compose with AND and report active constraints and result counts. Search must not treat hidden metadata or answer text as lesson content.

`linkedQuestionIds` contains unique existing `q-` or `gq-` IDs in display order. Material may preview eligible Practice questions. Review items stay visibly unscored. Mock Exam links include only scoreable IDs under the canonical scoring boundary; a missing, rejected, duplicate, or stale ID is a validation error, not silently ignored.

## Study Language and Direction

The page shell follows the configured study language. Arabic narrative uses `lang="ar" dir="rtl"`; English protocol names, IP addresses, commands, formulas, and source labels inside Arabic text use isolated `bdi dir="ltr"`. Controls keep logical start/end alignment, and mixed-direction punctuation must be visually checked on narrow and wide layouts. A translation must preserve source meaning, flag ambiguity, and never turn generated guidance into official source text.

## Coverage Report

The coverage report lists every module, objective, and lesson; source locations used; content sections present; allowed omissions with reasons; linked-question IDs; translation status; and review status. It fails coverage when an objective has no lesson, a lesson has no source reference, an item claims unsupported content, or an omission is not recorded.

## Lesson Quality Checks

Release validation must check:

- coverage of every configured module and objective, with all allowed omissions recorded;
- unsupported claims and examples against accepted source locations;
- semantic duplication within and across lessons, retaining intentional reinforcement only;
- faithful translation, study-language consistency, and no false official attribution;
- LTR/RTL structure, isolated technical tokens, focus order, and responsive readability;
- short paragraphs, concise recap points, clear headings, and accessible reading level;
- valid, non-empty source references at lesson and compiled-item level; and
- unique existing linked-question IDs with Practice and Mock Exam eligibility enforced.

Any failed check sets the appropriate canonical review flags and prevents scoreable use where `04-CONTENT-AND-DATA-CONTRACTS.md` requires approval.
