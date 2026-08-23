# Question Generation Specification

## Purpose and Contract

Generation consumes accepted lesson content, canonical lesson/module/objective IDs, study language, content policy, source references, and configured quotas. It produces generated questions and generated study explanations for Practice, Mock Exam, Question Bank, and Question Explanations while preserving the canonical contracts in `04-CONTENT-AND-DATA-CONTRACTS.md`.

The authoring field `bloomLevel` is the generation profile's name for the canonical Bloom/cognitive concept. Its allowed values are `remember`, `apply`, and `analyze`; it must equal canonical `cognitiveLevel` on the generated record. It narrows, and does not redefine, the wider canonical cognitive-level vocabulary.

## Default Generation Profile

Six MCQs, four True/False items, 30/50/20 difficulty, and 25/50/25 Bloom are defaults unless project configuration overrides them. A zero per-lesson count disables that generated question type; at least one type must remain enabled in a mode that permits generated questions. `source-only` instead requires both generated targets to be zero and skips generation. For `L` sufficiently supported lessons with per-lesson targets `M` MCQs and `T` True/False items, the full target batch has `N = (M + T)L` questions. With the default counts and no reported shortfall, `N = 10L` and difficulty counts are exactly `easy = 3L`, `medium = 5L`, and `hard = 2L`.

Convert each configured percentage distribution to whole-question counts with largest-remainder allocation: multiply `N` by each percentage, divide by 100, take each floor, then assign remaining questions in descending fractional-remainder order. Difficulty ties use `easy`, `medium`, `hard`; Bloom ties use `analyze`, `remember`, `apply`. Record every residual recipient. Under the default Bloom profile, this yields `apply = 5L`, `remember = floor(5L / 2)`, and `analyze = N - apply - remember`; an odd `L` gives the single indivisible residual to `analyze`. Any unreported residual or deviation without a content shortfall fails generation QA. With the default four True/False items, every fully supported lesson has exactly two True and two False answers.

For reproducible default True/False answer order, sort the lesson's four records by stable `gq-` ID. Compute SHA-256 over the UTF-8 bytes of `project.slug`, one literal line-feed byte, and `lesson.id`; parse the first eight hexadecimal digits as an unsigned integer and take it modulo 6. Use the result as the zero-based index into this fixed pattern list: `TTFF`, `TFTF`, `TFFT`, `FTTF`, `FTFT`, `FFTT`. Assign the sorted records those truth values, where `T` uses `correctAnswer: true` and `F` uses `correctAnswer: false`.

For a configured non-default True/False count, compute SHA-256 over the UTF-8 bytes of `project.slug`, one line-feed, and each stable `gq-` ID; sort the full generated True/False pool by hash and then ID, and call its size `P`. The first `floor(P / 2)` records are True and the next `floor(P / 2)` are False. When `P` is odd, the final record is True if the least-significant bit of the final digest byte in the SHA-256 hash of `project.slug` is zero, and False if it is one; record which value received the extra item. This keeps full-pool balance within one while varying record order reproducibly. Generation QA recomputes the applicable mapping; a different order fails. A reported shortfall is exempt from its original target mapping but must report the produced True/False balance explicitly.

“Sufficiently supported” means the lesson has accepted evidence that can support the prompt, answer, rationale, and every distractor or corrected statement without outside facts. Quotas are targets, never permission to invent content.

## Quota Shortfall Report

If evidence cannot safely meet a quota, emit a shortfall rather than a weak question. The report records release ID, lesson ID, objective ID, requested and produced counts by type, difficulty, and `bloomLevel`; True/False answer balance; missing slots; checked `sourceRefs`; reason code; explanation; and review owner. It also records the integer allocation residual and ordered recipient list for both configured distributions; each residual is from zero through two because there are three buckets. Under the defaults, the Bloom residual is `0` or `1`, and a value of `1` names `analyze` and states that `L` was odd. Reason codes include `insufficient-evidence`, `answer-ambiguity`, `duplicate`, `translation-risk`, and `review-rejection`. Release QA compares the report with the generation profile and does not silently backfill from another objective or outside sources.

## MCQ Rubric

Every MCQ must satisfy all of these checks:

1. It has exactly four non-empty, parallel options.
2. Exactly one zero-based answer index is correct under the cited evidence.
3. It assesses exactly one canonical learning objective.
4. Each distractor is plausible for the same scenario and has a specific rejection rationale.
5. Grammar, length, ordering, repetition, absolutes, and formatting do not cue the answer.
6. Prompt, options, answer, and rationales add no unsupported fact.
7. It has a concise correct-answer `rationale` plus four `distractorRationales` slots aligned by option index; the correct option's slot states why it is not a distractor.

An application item requires the learner to use the source concept in a scenario; swapping nouns in a recall statement does not make it `apply`.

## True/False Rubric

Every True/False item must satisfy all of these checks:

1. It states one testable proposition.
2. It contains no double negative.
3. A false item is not a trivial one-word flip of a source sentence.
4. Absolutes such as “always” and “never” appear only when the evidence supports the absolute.
5. Answer balance follows the configured deterministic pool rule; the default four-item lesson set has exactly two True and two False answers.
6. It includes a source-grounded rationale for the answer.
7. When false, `correctedStatement` contains a complete corrected false statement; when true, `correctedStatement` is null.

## Evidence and Ambiguity

Every generated question has at least one `sourceRef` and a non-empty canonical `evidenceMap`. Each evidence entry has a non-empty `claimId`, one exact `target`, non-empty `sourceRefs`, and `support` of `direct` or `derived`. For an MCQ, the map must contain exactly one entry for every claim-bearing target: `prompt`, `correctAnswer`, `rationale`, `options[0]` through `options[3]`, and `distractorRationales[0]` through `distractorRationales[3]`. A generic question-level entry cannot satisfy this requirement. A reviewer must be able to reach each claim's exact location. Translation uses the configured study language; Arabic content is `lang="ar" dir="rtl"`, while protocol names, IP addresses, commands, and option labels are isolated LTR.

Reject an item for answer ambiguity when more than one option can be defended, the answer changes under a reasonable reading, a missing condition is required, the source conflicts, or translation changes the proposition. Do not repair ambiguity by making distractors absurd. Record the rejected item and provenance.

## Semantic Duplicate Checks

Run the deterministic canonical normalization and comparison from `04-CONTENT-AND-DATA-CONTRACTS.md`: Unicode NFKC, trim, whitespace collapse, casefold, punctuation removal, same-type comparison, and lexicographic candidate order. Compare semantic proposition, scenario conditions, assessed objective, answer, and evidence—not prompt text alone. Exact official matches are rejected as duplicates. Among exact generated matches only the lowest `gq-` ID is retained. Near matches, translated paraphrases, same-answer scenario clones, or evidence conflicts receive `duplicateDisposition: needs-review`; they are not scoreable until resolved.

## Review States and Canonical Mapping

`review.status` is one of `draft`, `validated`, `human-reviewed`, `needs-review`, or `rejected`. Generated-question records must satisfy this complete cross-field truth table:

| `review.status` | `qualityState` | `reviewState` | `needsReview` | `review.approval` |
| --- | --- | --- | --- | --- |
| `draft` | `draft` | `unreviewed` | `true` | Absent. |
| `validated` | `validated` | `unreviewed` | `false` | Absent. |
| `human-reviewed` | `approved` | `approved` | `false` | `status: completed`, `decision: approved`. |
| `needs-review` | `needs-review` | `needs-review` | `true` | Completed human decision `needs-review`. |
| `rejected` | `rejected` | `rejected` | `true` | Completed human decision `rejected`. |

For every present approval, `reviewedRecordId` equals the generated question `id`, and `reviewedContentVersion` equals its top-level `contentVersion`. The full immutable Review approval fields (`reviewedRecordId`, `reviewedContentVersion`, canonical `status`, `decision`, `reviewer`, `reviewedAt`, `reason`, and `notes`) remain required by the canonical contract. A rejected or needs-review human decision therefore cannot retain approved states, and a stale or differently bound approval does not apply to edited content.

## Route Eligibility

Question Bank may show every retained item with origin, evidence, duplicate, and review labels. Normal scored Practice may use `validated` or `human-reviewed` items when `needsReview` is false, the truth-table states match, `duplicateDisposition` is `retain`, and the answer and evidence are valid. `needs-review` items may appear only in an explicitly unscored review mode. Draft and rejected items are not learner-facing.

When `generatedQuestionsRequireHumanReviewForExam` is true, human approval is mandatory for every Mock Exam item: `review.status`, `qualityState`, and `reviewState` must be `human-reviewed`, `approved`, and `approved`, and the current version-bound approval must be completed and approved. Eligibility requires the complete exact approval contract: matching `reviewedRecordId` and `reviewedContentVersion`, `status: completed`, `decision: approved`, a non-empty `reviewer`, a valid ISO 8601 UTC `reviewedAt`, and non-empty `reason` and `notes`. Missing, empty, malformed, or stale approval evidence is ineligible. When `generatedQuestionsRequireHumanReviewForExam` is false, a validated item may enter Mock Exam if it meets the same scoreability, evidence, answer, and duplicate rules as scored Practice. Mock Exam never includes draft, needs-review, rejected, duplicate, ambiguous, or stale-review items. Regardless of configuration, any high-stakes, credentialing, admissions, employment, compliance, or externally reported assessment requires human review and that same complete approval evidence. Automated validation alone never authorizes high-stakes use.

## Claims and Labels

Generated records must be labelled “Generated practice question” and explanations “Generated study guidance.” Prohibited claims include `official exam question`, “official question,” “from the exam,” “past-paper question,” “certified,” “guaranteed to appear,” or any wording that implies source authors, schools, vendors, or exam bodies wrote, approved, or endorsed generated content. A source reference proves grounding; it does not make generated text official.

## Release Checks

Release QA validates quotas and shortfalls, both rubrics, one-objective linkage, source and evidence coverage, difficulty/Bloom distributions, True/False balance, answer ambiguity, semantic duplicates, faithful translation, RTL/LTR behavior, review-version currency, Practice eligibility, Mock Exam eligibility, and prohibited claims. A failed check routes the record to review or rejection and never relaxes the scoring boundaries.
