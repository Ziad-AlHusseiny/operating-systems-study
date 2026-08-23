# Content and Data Contracts

## Global Rules

All records are JSON objects with exact required fields for their type; consumers may reject unknown schema versions. IDs are unique and immutable within a release. Stable prefixes are `source-`, `module-`, `objective-`, `lesson-`, `q-`, and `gq-`. `sourceRef` always preserves the original evidence and does not point to an inferred answer. All date-times are ISO 8601 UTC strings and versions are semantic strings.

## Project Configuration

`project-config.json` has exactly the approved nested shape shown by
`examples/project-config.example.json`. It has no top-level `projectId` field.
`project.slug` is the unique, immutable project identifier; every downstream
field named `projectId` must equal that slug.

| Top-level field | Type | Exact rule |
| --- | --- | --- |
| `version` | integer | Exactly `1`. |
| `project` | object | Exactly `title`, `shortTitle`, `slug`, `description`, `brandInitials`, `sourceLanguage`, and `studyLanguage`. All are non-empty strings; both languages are BCP 47 tags, and `slug` is lowercase words separated by single hyphens. |
| `contentPolicy` | object | Exactly `mode`, `allowOutsideSources`, and `generatedQuestionsRequireHumanReviewForExam`. |
| `questionGeneration` | object | Exactly `mcqPerLesson`, `trueFalsePerLesson`, `difficultyPercent`, and `bloomPercent`. |
| `exam` | object | Exactly positive-integer `defaultCount` and `defaultMinutes`. |
| `deployment` | object | Exactly `provider`, `repository`, `branch`, and `publicUrl`. |

`contentPolicy.mode` is exactly `source-only`, `source-plus-generated`, or
`generated-only`; its other two fields are Booleans.
`questionGeneration.mcqPerLesson` and `trueFalsePerLesson` are non-negative
integers. A zero target disables that generated question type. Both are zero
only in `source-only` mode; every mode that permits generated questions requires
at least one positive target. `difficultyPercent` has exactly numeric `easy`, `medium`, and `hard`
fields, while `bloomPercent` has exactly numeric `remember`, `apply`, and
`analyze` fields. Each percentage is from 0 through 100 and each object totals
exactly 100. `deployment.provider` is `github-pages`, `repository` uses
`OWNER/REPOSITORY`, `branch` is non-empty, and `publicUrl` is an HTTP(S) URL.

## Source Manifest and `sourceRef`

The source manifest has exactly `version` and `sources` as its required top-level fields. Each source requires `id` (`source-` prefix), `fileName`, `collection`, `label`, `format`, `checksum`, `status`, and `locations`. `collection` is the configured grouping used by source filters, and `label` is its non-empty learner-facing source name; neither is inferred from the filename. PDF sources additionally require `pages`; PPTX sources additionally require `slides`. No other source format permits a `pages` or `slides` field in the manifest. A source status is `inventoried`, `extracted`, `visually-checked`, `normalized`, `accepted`, or `needs-review`.

| Source format | Required count | Only compatible `locationType` |
| --- | --- | --- |
| `pdf` | `pages` | `page` |
| `pptx` | `slides` | `slide` |
| `docx` | None | `section` |
| `text` | None | `section` |
| `markdown` | None | `section` |
| `csv` | None | `row` |
| `json` | None | `section` |
| `image` | None | `image` |

The canonical `docx` format also represents converted Word-compatible `.doc`,
`.odt`, and `.rtf` sources; `pptx` also represents converted `.ppt` and `.odp`
slide decks. `fileName` and `checksum` always identify the preserved original,
while the source audit records the working derivative and conversion evidence.

| Field | Type | Rule |
| --- | --- | --- |
| `sourceRef.sourceId` | string | Existing `source-` ID. |
| `sourceRef.locationType` | string | Exactly one of `page`, `slide`, `section`, `row`, `image`. |
| `sourceRef.location` | integer or string | Original page/slide/row number or stable section/image locator. |
| `sourceRef.context` | string | Optional human-readable span or region. |
| `sourceRef.confidence` | number | Optional 0–1 extraction confidence. |

`sourceRefs` is a non-empty array whenever a content record claims source-derived content. A reference must name a manifest source and a location compatible with that source format.

## Learning Structure

| Record | Exact required fields | Rules |
| --- | --- | --- |
| Module | `id`, `title`, `order`, `objectiveIds`, `sourceRefs` | ID begins `module-`; objectives are ordered and unique. |
| Objective | `id`, `moduleId`, `text`, `order`, `sourceRefs` | ID begins `objective-`; parent module exists. |
| Lesson | `id`, `moduleId`, `objectiveIds`, `title`, `body`, `origin`, `generatedStudyGuidance`, `contentVersion`, `sourceRefs`, `needsReview`, `reviewNotes` | ID begins `lesson-`; `origin` is `source` or `generated`; `generatedStudyGuidance` is true exactly for generated guidance; source-derived body has references; `contentVersion` identifies the version reviewed. |

## Material Sections

Each material section requires exactly `id`, `lessonId`, `title`, `origin`, `generatedStudyGuidance`, `summaries`, `terms`, `examples`, `mistakes`, `examTips`, `recaps`, `sourceRefs`, `linkedQuestionIds`, `contentVersion`, `needsReview`, and `reviewNotes`. `id` is unique and `lessonId` must identify an existing `lesson-` record. `origin` is exactly `source` or `generated`, and `generatedStudyGuidance` is true exactly when `origin` is `generated`; the UI displays the corresponding source or generated label. A page that needs both origins uses separate labelled sections rather than merging their claims. `contentVersion` identifies the compiled lesson version. `sourceRefs` is the section-level evidence set; every non-empty item below also carries its own non-empty `sourceRefs` so a learner-facing claim remains traceable.

| Field | Type | Rule |
| --- | --- | --- |
| `summaries` | array of `{body, sourceRefs}` | Ordered source-grounded summaries. |
| `terms` | array of `{term, definition, sourceRefs}` | Definitions without inferred meaning. |
| `examples` | array of `{title, body, sourceRefs}` | Worked or contextual examples. |
| `mistakes` | array of `{misconception, correction, sourceRefs}` | A mistake and its supported correction. |
| `examTips` | array of `{body, sourceRefs}` | Exam-facing advice grounded in source material. |
| `recaps` | array of `{body, sourceRefs}` | Short revision recaps. |
| `linkedQuestionIds` | array | Unique existing `q-` or `gq-` IDs, in display order. |

## Questions

All question types require `id`, `origin`, `type`, `prompt`, `topic`, `correctAnswer`, `contentVersion`, `sourceRefs`, `needsReview`, and `reviewNotes`. `origin` is exactly `official` or `generated`; `sourceRefs` use the contract above. `contentVersion` is the semantic version to which a review approval binds. Official question IDs begin `q-`; generated IDs begin `gq-`; IDs never change when a question is reviewed.

| Type | Required type-specific fields | `correctAnswer` |
| --- | --- | --- |
| `mcq` | `options` (exactly four non-empty strings) | Zero-based index of one option. |
| `true-false` | `options` exactly `["True", "False"]` | `0` or `1`. |
| `true-false-group` | `statements` array of `{id, text}` | Object mapping every statement ID to a Boolean. |
| `multi-select` | `options` (two or more non-empty strings) | Non-empty array of unique zero-based indices. |
| `matching` | `leftItems`, `rightItems`, each `{id, text}` | Object mapping every left ID to one right ID; right IDs are unique unless `allowManyToOne` is true. |
| `ordering` | `items` array of `{id, text}` | Array of every item ID in correct order. |

An official question additionally requires `duplicateSources` (array) and `officialExplanation` (string). Its answer may only come from an explicit official answer key. When that answer is absent or unreliable, and only for an official question with `needsReview: true`, `correctAnswer` is `null` and `reviewNotes` is non-empty; the type-specific prompt/options/statements/items remain complete, and the item is unscored and excluded from Mock Exam. A generated question and an official question with `needsReview: false` always require the valid type-specific answer shown above. Generated reasoning never overwrites an official record.

## Generated Question Quality and Duplication

A generated question supports only `mcq` and `true-false`. In addition to the base and applicable type-specific question fields, its generated-specific common field set is exactly `rationale`, `difficulty`, `bloomLevel`, `cognitiveLevel`, `learningObjectiveId`, `generationMethod`, `generatedExplanationId`, `provenance`, `evidenceMap`, `qualityState`, `reviewState`, `duplicateComparison`, `duplicateDisposition`, and `review`. The base `contentVersion` remains required. A generated MCQ uses the `mcq` row above. A generated True/False item uses `prompt` as its single testable statement, has no `options`, stores a Boolean `correctAnswer`, and requires `correctedStatement`: null when true and a non-empty complete correction when false. This generated representation intentionally replaces the numeric, option-based official True/False form. `provenance` requires exactly `sourceRefs`, `modelVersion`, and `promptVersion`; `generatedExplanationId` identifies an explanation record.

| Field | Type | Allowed values or rule |
| --- | --- | --- |
| `rationale` | string | Non-empty evidence-based explanation of the correct answer. |
| `difficulty` | string | Exactly `easy`, `medium`, or `hard`. |
| `bloomLevel` | string | Exactly `remember`, `apply`, or `analyze`; equals `cognitiveLevel`. |
| `cognitiveLevel` | string | Exactly `remember`, `understand`, `apply`, `analyze`, `evaluate`, or `create` (Bloom level). |
| `learningObjectiveId` | string | Existing `objective-` ID assessed by the item. |
| `contentVersion` | string | Semantic content version reviewed by any approval. |
| `evidenceMap` | array | Non-empty `{claimId, target, sourceRefs, support}` records; `target` identifies one required claim-bearing field and `support` is exactly `direct` or `derived`. |
| `qualityState` | string | Exactly `draft`, `validated`, `needs-review`, `approved`, or `rejected`. |
| `reviewState` | string | Exactly `unreviewed`, `needs-review`, `approved`, or `rejected`. |
| `duplicateComparison` | object | Exactly `algorithmVersion`, `normalizedPrompt`, `candidateIds`, and `matchClass`; `matchClass` is `none`, `exact`, `near`, or `conflict`. |
| `duplicateDisposition` | string | Exactly `retain`, `reject-duplicate`, or `needs-review`. |
| `review` | object | Generated review view with `status` and conditional version-bound `approval` under the review contract below. |

Duplicate comparison is deterministic: normalize prompts with Unicode NFKC, trim, collapse internal whitespace, casefold, and remove punctuation; compare only questions with the same `type`; and process candidate IDs in lexicographic question ID order. No exact match yields `retain`. An exact match with an official `q-` yields `reject-duplicate`. Among exact generated matches, retain only the lexicographically lowest `gq-` ID and mark every other candidate `reject-duplicate`. A `near` match or conflicting evidence yields `needs-review`; it cannot be scoreable until reviewed. Detailed authoring rubrics are defined in [06-QUESTION-GENERATION-SPEC.md](06-QUESTION-GENERATION-SPEC.md).

## Question Explanation

| Field | Type | Rule |
| --- | --- | --- |
| `id` | string | Unique `explanation-` ID. |
| `questionId` | string | Existing `q-` or `gq-` ID. |
| `language` | string | BCP 47 study-language tag. |
| `generatedStudyGuidance` | boolean | Exactly `true`; this record is never an official answer. |
| `translation` | string | Complete non-empty study-language translation of the question. |
| `explanation` | array | Two or three non-empty short explanation paragraphs. |
| `body` | string | Concise answer explanation without unsupported claims. |
| `note` | string | Non-empty revision note that preserves the generated label. |
| `contentVersion` | string | Semantic content version reviewed by any approval. |
| `sourceRefs` | array | Non-empty evidence for every material claim. |
| `needsReview` / `reviewNotes` | boolean / string | Review state and reason. |
| `review` | object | Generated review view with `status` and conditional version-bound `approval`. |

## Review State and Scoring

Every version-bound canonical lesson, material section, question, and explanation has `needsReview`, `reviewNotes`, and a semantic `contentVersion`. Review decisions are immutable records; a new review supersedes a prior one without deleting it. An approval applies only when `reviewedRecordId` equals the current record ID and `reviewedContentVersion` equals its current top-level `contentVersion`.

| Record | Exact required fields | Allowed values and scoring effect |
| --- | --- | --- |
| Review approval | `reviewedRecordId`, `reviewedContentVersion`, `status`, `decision`, `reviewer`, `reviewedAt`, `reason`, `notes` | `status` is exactly `pending` or `completed`; `decision` is exactly `approved`, `rejected`, or `needs-review`. `reviewer` is a non-empty reviewer ID, `reviewedAt` is ISO 8601 UTC, and `reason`/`notes` are strings. The content/schema version reviewed is preserved in `reviewedContentVersion`. |

`needsReview: true`, `decision: needs-review`, or `decision: rejected` means the record is visibly labelled “Needs review — unscored” and excluded from every score, result, practice aggregate, and Mock Exam pool. A scoreable official record must have `needsReview: false`, a valid type-specific answer, valid source references, and a completed approved review when the project policy requires review. A generated record is eligible for scored Practice when it has `needsReview: false`, `review.status: validated` or `human-reviewed`, the corresponding `qualityState: validated` or `approved`, a compatible `reviewState`, `duplicateDisposition: retain`, a valid type-specific answer, and valid evidence. Mock Exam applies the additional configured human-review gate defined in `06-QUESTION-GENERATION-SPEC.md`. Rejection retains the item and its provenance.

## LocalStorage Progress

The LocalStorage key is the literal prefix `study-site-progress:` followed
immediately by the canonical `project.slug` value (for example,
`study-site-progress:network-fundamentals-study`). Its versioned object has
exact required fields `version`, `projectId`, `updatedAt`, `lessonProgress`,
`questionProgress`, `bookmarks`, and `mistakes`. `lessonProgress` maps `lesson-`
IDs to `{status, lastVisitedAt}`; `questionProgress` maps `q-`/`gq-` IDs to
`{attempts, correctAttempts, lastAnswer, lastAttemptAt}`. Unknown versions are
preserved or migrated explicitly, never interpreted silently. The stored
`projectId` is a compatibility field whose value must equal `project.slug`.

## Sessions and Results

| Record | Exact required fields | Rules |
| --- | --- | --- |
| Session | `id`, `projectId`, `mode`, `questionIds`, `startedAt`, `status` | `projectId` equals `project.slug`; `questionIds` contain only eligible, scoreable question IDs. |
| Result | `id`, `sessionId`, `questionId`, `answer`, `isCorrect`, `scored`, `answeredAt` | `scored` is false for review items; `isCorrect` is null when unscored. |

Sessions and results retain the exact question IDs and answer payloads used at the time. They may report accuracy only from records where `scored` is true.
