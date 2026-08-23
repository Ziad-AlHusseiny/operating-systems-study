# Resumable build workflow

This workflow turns an approved project input, configuration, and source set
into a traceable static study site. Run stages in order. A downstream stage may
consume only outputs whose upstream gate passed. Paths below are the standard
project paths; record any project-specific command or path in the ledger.

## Resume contract

Keep `progress-ledger.md` at the project root. Before a stage starts, compute
SHA-256 hashes for every input file and record them. After the stage passes its
gate, hash every durable output and commit the entry with the outputs. Status is
one of `pending`, `in-progress`, `blocked`, or `complete`; `complete` means the
named validation passed, not merely that files were written.

A valid entry has this exact shape:

```text
Stage 4: complete
Inputs: input/materials/course.pdf sha256=<hash>
Outputs: reports/SOURCE_AUDIT_REPORT.md sha256=<hash>
Validation: passed
Open reviews: source-01 page 18
Next stage: 5
```

List every input and output on its own continuation line when a stage has more
than one. Open reviews must contain stable record IDs and locations, or `none`.
Never mark a stage complete while its blocking gate is failing.

On resume, compare the recorded input hashes with current hashes. Do not
reprocess a completed stage when all input hashes are unchanged and every
recorded output exists with its recorded hash. Resume at its `Next stage`.
When an input or output hash differs, mark that stage and every dependent stage
`pending`, keep the old ledger entries as history, and rebuild only the affected
chunks. A changed source does not invalidate unrelated modules.

Process content in restartable chunks: one module at a time, or a stable,
inclusive ID range such as `q-001..q-050` or `gq-module-02-001..050`. A chunk
entry records its input hashes, output hashes, validation result, and review
items. Never use changing row positions, timestamps, or generation order as
chunk identity. Write intermediate output outside the final delivery path and
replace a final artifact only after the complete chunk validates.

## Stage 1: Initialize project

- **Inputs:** `input/PROJECT_INPUT.md`, `input/project-config.json`, this kit,
  and the existing static-site implementation base.
- **Actions:** validate required values, copy the standard project structure,
  pin tool/runtime versions, record the repository, branch, and intended
  deployment target, and initialize `progress-ledger.md`. Do not publish.
- **Outputs:** initialized `input/`, `content/`, `scripts/`, `reports/`, and
  `study-website/` directories; validated configuration; ledger entry.
- **Gate:** initialization checkpoint: the two inputs parse and the structure is
  complete. Gate 1 closes after Stage 2 reconciles the material inventory and
  blocks Stage 3 until then.
- **Resume condition:** skip only when the two input hashes, tool versions, and
  initialized structure match the completed entry; otherwise revalidate.

## Stage 2: Inventory sources

- **Inputs:** validated project configuration and every file under
  `input/materials/`.
- **Actions:** hash each file, assign stable `source-` IDs, identify format,
  size, password/corruption/support status, and page or slide counts when
  readable; never silently omit a file.
- **Outputs:** `content/source-manifest.json` with one record per supplied file
  and a source-inventory section in `reports/SOURCE_AUDIT_REPORT.md`.
- **Gate:** Gate 1, Input Completeness.
- **Resume condition:** reuse an unchanged manifest record by source hash;
  inventory only new or changed files and re-run the complete manifest check.

## Stage 3: Extract and render sources

- **Inputs:** accepted source-manifest records and original source files.
- **Actions:** use format-appropriate text extraction, render every page or
  slide needed for visual inspection, run OCR only where necessary, and retain
  exact page/slide/section/image locations with tool versions and confidence.
- **Outputs:** durable extracted text and rendered assets organized by
  `source-` ID, plus extraction records in
  `reports/SOURCE_AUDIT_REPORT.md`.
- **Gate:** the extraction-coverage portion of Gate 2, Extraction and
  Provenance.
- **Resume condition:** resume by `source-` ID and page/slide range; do not
  repeat a completed range whose source hash and extraction settings match.

## Stage 4: Audit provenance and confidence

- **Inputs:** source manifest, extracted text, rendered pages/slides, OCR
  confidence, and detected question/answer-key locations.
- **Actions:** compare extraction with visible sources, record unreadable and
  low-confidence locations, verify only visible OCR corrections, group source
  duplicates, and create stable review items for ambiguity or contradiction.
- **Outputs:** completed `reports/SOURCE_AUDIT_REPORT.md` with counts, coverage,
  corrections, confidence, duplicate groups, answer-key status, and review
  items.
- **Gate:** Gate 2, Extraction and Provenance.
- **Resume condition:** audit only changed source chunks, then recompute report
  totals and references; unchanged audited chunks remain complete.

## Stage 5: Build module/objective/lesson map

- **Inputs:** Gate-2-approved source inventory and project scope.
- **Actions:** map sources to stable `module-`, `objective-`, and `lesson-` IDs;
  define lesson order, source coverage, and supported question targets; expose
  omissions and overlaps rather than filling them with unsupported content.
- **Outputs:** canonical module/objective/lesson map and the baseline
  `reports/CONTENT_COVERAGE_REPORT.md`.
- **Gate:** the stable-ID, coverage, and source-reference parts of Gates 3 and
  4.
- **Resume condition:** rebuild the affected module only when its source hashes
  or approved mapping changes, then recheck global ID uniqueness.

## Stage 6: Author Material lessons

- **Inputs:** approved module/objective/lesson map, extracted source chunks,
  study-language rules, and the lesson contract.
- **Actions:** author source-backed summaries, explanations, terms, examples,
  mistakes, tips, and recaps in module chunks; preserve official/generated
  labels; link supported questions; record unsupported optional sections.
- **Outputs:** `content/lessons/` records and updated
  `reports/CONTENT_COVERAGE_REPORT.md` with per-lesson coverage and omissions.
- **Gate:** Gate 4, Lessons and Guidance.
- **Resume condition:** resume by `module-` or `lesson-` ID; unchanged approved
  lesson records are reused, while changed chunks receive a new content version
  and review state.

## Stage 7: Canonicalize official questions

- **Inputs:** source question/answer locations, visible marks, source manifest,
  data contract, and approved objective map.
- **Actions:** transcribe faithfully, assign stable `q-` IDs, preserve all
  duplicate source references, normalize only presentation, and make conflicts,
  missing answers, or uncertain text review-only and unscored.
- **Outputs:** `content/official-questions/` records, canonical duplicate map,
  and official-question coverage in `reports/QUESTION_QUALITY_REPORT.md`.
- **Gate:** Gate 3, Canonical Content.
- **Resume condition:** resume by stable `q-` range; do not regenerate
  unchanged canonical records, and recheck all IDs and duplicate groups after
  merging chunks.

## Stage 8: Generate MCQ and True/False pools

- **Inputs:** approved lesson/objective chunks, allowed source evidence,
  generation quotas, and question rubrics.
- **Actions:** generate only supported items; attach claim-level evidence,
  rationales, difficulty, cognitive level, and review state; detect semantic
  duplicates and report quota shortfalls without padding the pool.
- **Outputs:** `content/generated-questions/` records and expanded
  `reports/QUESTION_QUALITY_REPORT.md` with targets, achieved counts,
  shortfalls, duplicate decisions, and rubric results.
- **Gate:** preliminary Gate 5, Generated Questions; generated items remain
  ineligible for Mock Exams until the required review is complete.
- **Resume condition:** resume by lesson or stable `gq-` range; preserve IDs for
  unchanged records and regenerate only invalidated chunks.

## Stage 9: Run independent content review

- **Inputs:** lesson, official-question, generated-question, explanation,
  coverage, provenance, and question-quality artifacts.
- **Actions:** have a reviewer independently compare claims and answers with
  cited evidence, apply the review truth table, resolve duplicates, and record
  approvals against both record ID and content version. Never self-resolve an
  evidence gap by guessing.
- **Outputs:** version-bound approval records, corrected review states, final
  `reports/CONTENT_COVERAGE_REPORT.md`, and final
  `reports/QUESTION_QUALITY_REPORT.md`.
- **Gate:** Gates 3, 4, and 5 all pass for content that will be scoreable or
  publicly labeled as reviewed.
- **Resume condition:** review only new or changed content versions; an old
  approval does not carry over to a changed version.

## Stage 10: Build deterministic payloads and integrate the static site

- **Inputs:** gate-approved canonical content, explicit review items, project
  configuration, and the UX/system-flow contract.
- **Actions:** sort records by stable IDs, serialize with fixed formatting,
  build delivery JSON from canonical sources, and integrate routes, labels,
  safe rendering, scoring, persistence, and accessibility. Generated delivery
  files are never edited by hand.
- **Outputs:** deterministic `study-website/data/` payloads and the complete
  static `study-website/` delivery folder, requiring no source files or build
  tools at runtime.
- **Gate:** Gate 6, Application Safety and Logic.
- **Resume condition:** if canonical input hashes and builder version match,
  `--check` must reproduce byte-identical outputs and integration is skipped;
  otherwise rebuild only affected payloads, then run the whole application gate.

## Stage 11: Run automated and browser QA

- **Inputs:** complete static delivery, canonical reports, test suites, and the
  browser matrix in `09-QA-GATES.md`.
- **Actions:** run Python validators, JSON parsing, JavaScript syntax checks,
  Node tests, whitespace checks, a local static server, and every desktop/mobile
  browser row; save commands, versions, results, screenshots/traces on failure,
  and relevant console output.
- **Outputs:** automated and browser evidence consolidated in
  `reports/FINAL_QA_REPORT.md`.
- **Gate:** Gates 6 and 7 both pass with no waived blocking failure.
- **Resume condition:** unchanged automated checks may be reused only within the
  same commit and tool versions; resume failed browser rows individually, then
  rerun smoke coverage across both viewports before marking complete.

## Stage 12: Handoff, deploy, and verify public output

- **Inputs:** Gate-7-approved commit, `reports/FINAL_QA_REPORT.md`, repository
  destination, and explicit deployment authorization from the project owner.
- **Actions:** prepare the maintainer handoff; stop before any push, workflow
  dispatch, or publish action unless that external action was explicitly
  authorized. When authorized, deploy the exact verified commit, monitor the
  GitHub Pages workflow, and verify public HTML, JSON counts, routes, and browser
  behavior.
- **Outputs:** final handoff summary and updated
  `reports/FINAL_QA_REPORT.md`; when deployment is authorized, also the workflow
  run reference, public URL, and public-verification evidence.
- **Gate:** Gate 8, Deployment. Without deployment authorization, record
  `not run — awaiting explicit authorization`; local completion is not public
  deployment success.
- **Resume condition:** if awaiting authorization, resume at the authorization
  check. If deployment was interrupted, inspect the remote workflow and public
  commit before retrying; never publish a different unverified commit.

## Stage invalidation and repair

A gate failure blocks dependent stages. Record the failure, evidence location,
owner, and smallest invalidated chunk in `progress-ledger.md`; set `Next stage`
to the earliest affected stage. Repair canonical inputs, rerun that stage's
validation, then rerun every downstream check whose input hash changed. Do not
delete failed evidence, rewrite history, use destructive Git reset, or mark a
known review item as passed.
