# Question Generation Specification

## Purpose and Contract

Generation consumes accepted lesson content, canonical lesson/module/objective IDs, study language, content policy, source references, and configured quotas. It produces generated questions and generated study explanations for Practice, Mock Exam, Question Bank, and Question Explanations while preserving the canonical contracts in `04-CONTENT-AND-DATA-CONTRACTS.md`.

The authoring field `bloomLevel` is the generation profile's name for the canonical Bloom/cognitive concept. Its allowed values are `remember`, `apply`, and `analyze`; it must equal canonical `cognitiveLevel` on the generated record. It narrows, and does not redefine, the wider canonical cognitive-level vocabulary.

## Default Generation Profile

For every sufficiently supported lesson, generate exactly six MCQs and four True/False items. For `L` sufficiently supported lessons, the full target batch has `N = 10L` questions: difficulty counts are exactly `easy = 3L`, `medium = 5L`, and `hard = 2L`. The configured 30/50/20 difficulty percentages are therefore met exactly when there is no reported shortfall.

The configured 25/50/25 Bloom percentages are targets subject to whole-question allocation. The only accepted deterministic allocation is `apply = 5L`, `remember = floor(5L / 2)`, and `analyze = N - apply - remember`. When `L` is even, this is exactly 25/50/25. When `L` is odd, `analyze` receives the single indivisible residual and exceeds `remember` by exactly one question; this one-item residual is permitted and must be recorded in the quota report. Any other residual, unreported residual, or deviation without a content shortfall fails generation QA. The four True/False answers for each fully supported lesson are balanced: exactly two True and two False, with answer order varied deterministically.

“Sufficiently supported” means the lesson has accepted evidence that can support the prompt, answer, rationale, and every distractor or corrected statement without outside facts. Quotas are targets, never permission to invent content.

## Quota Shortfall Report

If evidence cannot safely meet a quota, emit a shortfall rather than a weak question. The report records release ID, lesson ID, objective ID, requested and produced counts by type, difficulty, and `bloomLevel`; True/False answer balance; missing slots; checked `sourceRefs`; reason code; explanation; and review owner. It also always records `integerAllocationResidual` as `0` or `1`; a value of `1` names `analyze` as the recipient and states that `L` was odd. Reason codes include `insufficient-evidence`, `answer-ambiguity`, `duplicate`, `translation-risk`, and `review-rejection`. Release QA compares the report with the generation profile and does not silently backfill from another objective or outside sources.

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
5. Answer balance is enforced across the four-item lesson set.
6. It includes a source-grounded rationale for the answer.
7. When false, it includes a complete corrected false statement; when true, the correction field is null.

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
| `validated` | `validated` | `unreviewed` | `true` | Absent. |
| `human-reviewed` | `approved` | `approved` | `false` | `status: completed`, `decision: approved`. |
| `needs-review` | `needs-review` | `needs-review` | `true` | Completed human decision `needs-review`. |
| `rejected` | `rejected` | `rejected` | `true` | Completed human decision `rejected`. |

For every present approval, `reviewedRecordId` equals the generated question `id`, and `reviewedContentVersion` equals its top-level `contentVersion`. The full immutable Review approval fields (`reviewedRecordId`, `reviewedContentVersion`, canonical `status`, `decision`, `reviewer`, `reviewedAt`, `reason`, and `notes`) remain required by the canonical contract. A rejected or needs-review human decision therefore cannot retain approved states, and a stale or differently bound approval does not apply to edited content.

## Route Eligibility

Question Bank may show every retained item with origin, evidence, duplicate, and review labels. Practice may show `validated` or `needs-review` items only in an explicitly unscored review mode; normal scored Practice requires canonical `qualityState: approved`, `reviewState: approved`, `duplicateDisposition: retain`, a valid answer, and valid evidence. Mock Exam uses only that same scoreable set and never includes draft, merely validated, needs-review, rejected, duplicate, ambiguous, or stale-review items.

When `generatedQuestionsRequireHumanReviewForExam` is true, human approval is mandatory for every Mock Exam item. Regardless of configuration, any high-stakes, credentialing, admissions, employment, compliance, or externally reported assessment requires human review and completed approval. Automated validation alone never authorizes high-stakes use.

## Claims and Labels

Generated records must be labelled “Generated practice question” and explanations “Generated study guidance.” Prohibited claims include `official exam question`, “official question,” “from the exam,” “past-paper question,” “certified,” “guaranteed to appear,” or any wording that implies source authors, schools, vendors, or exam bodies wrote, approved, or endorsed generated content. A source reference proves grounding; it does not make generated text official.

## Release Checks

Release QA validates quotas and shortfalls, both rubrics, one-objective linkage, source and evidence coverage, difficulty/Bloom distributions, True/False balance, answer ambiguity, semantic duplicates, faithful translation, RTL/LTR behavior, review-version currency, Practice eligibility, Mock Exam eligibility, and prohibited claims. A failed check routes the record to review or rejection and never relaxes the scoring boundaries.
