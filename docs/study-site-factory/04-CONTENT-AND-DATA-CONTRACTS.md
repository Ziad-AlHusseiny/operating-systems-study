# Content and Data Contracts

## Global Rules

All records are JSON objects with exact required fields for their type; consumers may reject unknown schema versions. IDs are unique and immutable within a release. Stable prefixes are `source-`, `module-`, `objective-`, `lesson-`, `q-`, and `gq-`. `sourceRef` always preserves the original evidence and does not point to an inferred answer. All date-times are ISO 8601 UTC strings and versions are semantic strings.

## Project Configuration

| Field | Type | Rule |
| --- | --- | --- |
| `version` | string | Contract version. |
| `projectId` | string | Unique project identifier. |
| `title` | string | Learner-facing project title. |
| `studyLanguage` | string | BCP 47 language tag. |
| `contentPolicy` | object | Requires `officialOnly`, `generatedQuestionsEnabled`, and `reviewRequired`. |
| `sourceFiles` | array | Configured input file paths and expected formats. |
| `modules` | array | Ordered `module-` IDs. |

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

An official question additionally requires `duplicateSources` (array) and `officialExplanation` (string). Its answer may only come from an explicit official answer key. A generated question additionally requires `generationMethod`, `generatedExplanationId`, and `provenance` containing input `sourceRefs` and model/prompt version; it never overwrites an official record.

## Question Explanation

| Field | Type | Rule |
| --- | --- | --- |
| `id` | string | Unique explanation ID. |
| `questionId` | string | Existing `q-` or `gq-` ID. |
| `body` | string | Explains the answer without adding unsupported claims. |
| `sourceRefs` | array | Evidence for each material claim. |
| `needsReview` / `reviewNotes` | boolean / string | Review state and reason. |

## Review State and Scoring

Every reviewable record has `needsReview` and `reviewNotes`. `needsReview: true` means it is visibly labelled “Needs review — unscored”, excluded from every score, result, practice aggregate, and Mock Exam pool. A scoreable record must have `needsReview: false`, a valid type-specific answer, valid source references, and, for generated questions, explicit approval. Review approval records the reviewer, timestamp, decision, and reason; rejection retains the item and its provenance.

## LocalStorage Progress

LocalStorage uses key `study-site-progress:<projectId>` and a versioned object with exact required fields `version`, `projectId`, `updatedAt`, `lessonProgress`, `questionProgress`, `bookmarks`, and `mistakes`. `lessonProgress` maps `lesson-` IDs to `{status, lastVisitedAt}`; `questionProgress` maps `q-`/`gq-` IDs to `{attempts, correctAttempts, lastAnswer, lastAttemptAt}`. Unknown versions are preserved or migrated explicitly, never interpreted silently.

## Sessions and Results

| Record | Exact required fields | Rules |
| --- | --- | --- |
| Session | `id`, `projectId`, `mode`, `questionIds`, `startedAt`, `status` | `questionIds` contain only eligible, scoreable question IDs. |
| Result | `id`, `sessionId`, `questionId`, `answer`, `isCorrect`, `scored`, `answeredAt` | `scored` is false for review items; `isCorrect` is null when unscored. |

Sessions and results retain the exact question IDs and answer payloads used at the time. They may report accuracy only from records where `scored` is true.
