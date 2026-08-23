# Question Generation Specification

## Purpose and Contract

Generation consumes accepted lesson content, canonical lesson/module/objective IDs, study language, content policy, source references, and configured quotas. It produces generated questions and generated study explanations for Practice, Mock Exam, Question Bank, and Question Explanations while preserving the canonical contracts in `04-CONTENT-AND-DATA-CONTRACTS.md`.

The authoring field `bloomLevel` is the generation profile's name for the canonical Bloom/cognitive concept. Its allowed values are `remember`, `apply`, and `analyze`; it must equal canonical `cognitiveLevel` on the generated record. It narrows, and does not redefine, the wider canonical cognitive-level vocabulary.

## Default Generation Profile

For every sufficiently supported lesson, generate exactly six MCQs and four True/False items. The combined generated set targets exactly 30% easy, 50% medium, and 20% hard, and exactly 25% remember, 50% apply, and 25% analyze. Apply percentages over the release batch using deterministic largest-remainder allocation; for equal Bloom remainders, alternate the extra `remember` and `analyze` slot by lesson order so neither category is systematically favored. The four True/False answers for each fully supported lesson are balanced: exactly two True and two False, with answer order varied deterministically.

“Sufficiently supported” means the lesson has accepted evidence that can support the prompt, answer, rationale, and every distractor or corrected statement without outside facts. Quotas are targets, never permission to invent content.

## Quota Shortfall Report

If evidence cannot safely meet a quota, emit a shortfall rather than a weak question. The report records release ID, lesson ID, objective ID, requested and produced counts by type, difficulty, and `bloomLevel`; True/False answer balance; missing slots; checked `sourceRefs`; reason code; explanation; and review owner. Reason codes include `insufficient-evidence`, `answer-ambiguity`, `duplicate`, `translation-risk`, and `review-rejection`. Release QA compares the report with the generation profile and does not silently backfill from another objective or outside sources.

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

Every generated question has at least one `sourceRef` and a non-empty canonical `evidenceMap` covering the prompt claim, correct answer, rationales, and option-specific claims. A reviewer must be able to reach each claim's exact location. Translation uses the configured study language; Arabic content is `lang="ar" dir="rtl"`, while protocol names, IP addresses, commands, and option labels are isolated LTR.

Reject an item for answer ambiguity when more than one option can be defended, the answer changes under a reasonable reading, a missing condition is required, the source conflicts, or translation changes the proposition. Do not repair ambiguity by making distractors absurd. Record the rejected item and provenance.

## Semantic Duplicate Checks

Run the deterministic canonical normalization and comparison from `04-CONTENT-AND-DATA-CONTRACTS.md`: Unicode NFKC, trim, whitespace collapse, casefold, punctuation removal, same-type comparison, and lexicographic candidate order. Compare semantic proposition, scenario conditions, assessed objective, answer, and evidence—not prompt text alone. Exact official matches are rejected as duplicates. Among exact generated matches only the lowest `gq-` ID is retained. Near matches, translated paraphrases, same-answer scenario clones, or evidence conflicts receive `duplicateDisposition: needs-review`; they are not scoreable until resolved.

## Review States and Canonical Mapping

`review.status` is one of `draft`, `validated`, `human-reviewed`, `needs-review`, or `rejected`:

| Authoring status | Meaning and canonical effect |
| --- | --- |
| `draft` | Incomplete; canonical `qualityState: draft`, `reviewState: unreviewed`. |
| `validated` | Automated rubric checks passed; canonical `qualityState: validated`, still unreviewed. |
| `human-reviewed` | A human decision exists; only a completed approved decision for the current version can set both canonical states to `approved`. |
| `needs-review` | An unresolved evidence, ambiguity, translation, or duplicate issue; visibly unscored. |
| `rejected` | Retained with provenance, excluded from all scored use. |

This workflow field never replaces immutable Review approval fields (`reviewedRecordId`, `reviewedContentVersion`, canonical `status`, `decision`, `reviewer`, `reviewedAt`, `reason`, and `notes`). A stale approval does not apply to edited content.

## Route Eligibility

Question Bank may show every retained item with origin, evidence, duplicate, and review labels. Practice may show `validated` or `needs-review` items only in an explicitly unscored review mode; normal scored Practice requires canonical `qualityState: approved`, `reviewState: approved`, `duplicateDisposition: retain`, a valid answer, and valid evidence. Mock Exam uses only that same scoreable set and never includes draft, merely validated, needs-review, rejected, duplicate, ambiguous, or stale-review items.

When `generatedQuestionsRequireHumanReviewForExam` is true, human approval is mandatory for every Mock Exam item. Regardless of configuration, any high-stakes, credentialing, admissions, employment, compliance, or externally reported assessment requires human review and completed approval. Automated validation alone never authorizes high-stakes use.

## Claims and Labels

Generated records must be labelled “Generated practice question” and explanations “Generated study guidance.” Prohibited claims include `official exam question`, “official question,” “from the exam,” “past-paper question,” “certified,” “guaranteed to appear,” or any wording that implies source authors, schools, vendors, or exam bodies wrote, approved, or endorsed generated content. A source reference proves grounding; it does not make generated text official.

## Release Checks

Release QA validates quotas and shortfalls, both rubrics, one-objective linkage, source and evidence coverage, difficulty/Bloom distributions, True/False balance, answer ambiguity, semantic duplicates, faithful translation, RTL/LTR behavior, review-version currency, Practice eligibility, Mock Exam eligibility, and prohibited claims. A failed check routes the record to review or rejection and never relaxes the scoring boundaries.
