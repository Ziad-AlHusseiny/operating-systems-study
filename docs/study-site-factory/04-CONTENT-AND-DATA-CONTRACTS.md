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
`questionGeneration.mcqPerLesson` and `trueFalsePerLesson` are positive
integers. `difficultyPercent` has exactly numeric `easy`, `medium`, and `hard`
fields, while `bloomPercent` has exactly numeric `remember`, `apply`, and
`analyze` fields. Each percentage is from 0 through 100 and each object totals
exactly 100. `deployment.provider` is `github-pages`, `repository` uses
`OWNER/REPOSITORY`, `branch` is non-empty, and `publicUrl` is an HTTP(S) URL.

## Source Manifest and `sourceRef`

The source manifest has exactly `version` and `sources` as its required top-level fields. Each source requires `id` (`source-` prefix), `fileName`, `format`, `checksum`, `status`, and its applicable count (`pages` or `slides`) plus `locations`. A source status is `inventoried`, `extracted`, `visually-checked`, `normalized`, `accepted`, or `needs-review`.

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
| Lesson | `id`, `moduleId`, `objectiveIds`, `title`, `body`, `sourceRefs`, `needsReview`, `reviewNotes` | ID begins `lesson-`; source-derived body has references. |

## Material Sections

Each material section requires exactly `id`, `lessonId`, `title`, `summaries`, `terms`, `examples`, `mistakes`, `examTips`, `recaps`, `sourceRefs`, `linkedQuestionIds`, `needsReview`, and `reviewNotes`. `id` is unique and `lessonId` must identify an existing `lesson-` record. `sourceRefs` is the section-level evidence set; every non-empty item below also carries its own non-empty `sourceRefs` so a learner-facing claim remains traceable.

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

All question types require `id`, `origin`, `type`, `prompt`, `topic`, `correctAnswer`, `sourceRefs`, `needsReview`, and `reviewNotes`. `origin` is exactly `official` or `generated`; `sourceRefs` use the contract above. Official question IDs begin `q-`; generated IDs begin `gq-`; IDs never change when a question is reviewed.

| Type | Required type-specific fields | `correctAnswer` |
| --- | --- | --- |
| `mcq` | `options` (exactly four non-empty strings) | Zero-based index of one option. |
| `true-false` | `options` exactly `["True", "False"]` | `0` or `1`. |
| `true-false-group` | `statements` array of `{id, text}` | Object mapping every statement ID to a Boolean. |
| `multi-select` | `options` (two or more non-empty strings) | Non-empty array of unique zero-based indices. |
| `matching` | `leftItems`, `rightItems`, each `{id, text}` | Object mapping every left ID to one right ID; right IDs are unique unless `allowManyToOne` is true. |
| `ordering` | `items` array of `{id, text}` | Array of every item ID in correct order. |

An official question additionally requires `duplicateSources` (array) and `officialExplanation` (string). Its answer may only come from an explicit official answer key. It never overwrites an official record.

## Generated Question Quality and Duplication

A generated question requires the base question fields plus exactly `generationMethod`, `generatedExplanationId`, `provenance`, `difficulty`, `cognitiveLevel`, `evidenceMap`, `qualityState`, `reviewState`, `duplicateComparison`, and `duplicateDisposition`. `provenance` requires `sourceRefs`, `modelVersion`, and `promptVersion`; `generatedExplanationId` identifies an explanation record.

| Field | Type | Allowed values or rule |
| --- | --- | --- |
| `difficulty` | string | Exactly `easy`, `medium`, or `hard`. |
| `cognitiveLevel` | string | Exactly `remember`, `understand`, `apply`, `analyze`, `evaluate`, or `create` (Bloom level). |
| `evidenceMap` | array | Non-empty `{claimId, sourceRefs, support}` records; `support` is exactly `direct` or `derived`. |
| `qualityState` | string | Exactly `draft`, `validated`, `needs-review`, `approved`, or `rejected`. |
| `reviewState` | string | Exactly `unreviewed`, `needs-review`, `approved`, or `rejected`. |
| `duplicateComparison` | object | Exactly `algorithmVersion`, `normalizedPrompt`, `candidateIds`, and `matchClass`; `matchClass` is `none`, `exact`, `near`, or `conflict`. |
| `duplicateDisposition` | string | Exactly `retain`, `reject-duplicate`, or `needs-review`. |

Duplicate comparison is deterministic: normalize prompts with Unicode NFKC, trim, collapse internal whitespace, casefold, and remove punctuation; compare only questions with the same `type`; and process candidate IDs in lexicographic question ID order. No exact match yields `retain`. An exact match with an official `q-` yields `reject-duplicate`. Among exact generated matches, retain only the lexicographically lowest `gq-` ID and mark every other candidate `reject-duplicate`. A `near` match or conflicting evidence yields `needs-review`; it cannot be scoreable until reviewed. Detailed authoring rubrics belong to Task 4.

## Question Explanation

| Field | Type | Rule |
| --- | --- | --- |
| `id` | string | Unique explanation ID. |
| `questionId` | string | Existing `q-` or `gq-` ID. |
| `body` | string | Explains the answer without adding unsupported claims. |
| `sourceRefs` | array | Evidence for each material claim. |
| `needsReview` / `reviewNotes` | boolean / string | Review state and reason. |

## Review State and Scoring

Every reviewable record has `needsReview` and `reviewNotes`. Review decisions are immutable records; a new review supersedes a prior one without deleting it.

| Record | Exact required fields | Allowed values and scoring effect |
| --- | --- | --- |
| Review approval | `reviewedRecordId`, `reviewedContentVersion`, `status`, `decision`, `reviewer`, `reviewedAt`, `reason`, `notes` | `status` is exactly `pending` or `completed`; `decision` is exactly `approved`, `rejected`, or `needs-review`. `reviewer` is a non-empty reviewer ID, `reviewedAt` is ISO 8601 UTC, and `reason`/`notes` are strings. The content/schema version reviewed is preserved in `reviewedContentVersion`. |

`needsReview: true`, `decision: needs-review`, or `decision: rejected` means the record is visibly labelled “Needs review — unscored” and excluded from every score, result, practice aggregate, and Mock Exam pool. A scoreable official record must have `needsReview: false`, a valid type-specific answer, valid source references, and a completed approved review when the project policy requires review. A generated record is scoreable only when both `qualityState` and `reviewState` are `approved`, its duplicate disposition is `retain`, and its type-specific answer and source references are valid. Rejection retains the item and its provenance.

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
