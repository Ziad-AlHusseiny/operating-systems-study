# Blocking QA gates

These gates are release criteria, not suggestions. A gate record contains the
tested commit, input artifact hashes, command, tool version, start/end time,
exit status, measured counts, failures, and evidence paths. A pass is valid only
for those exact inputs. Never waive a blocking failure by describing it as a
known limitation; repair it or keep the release blocked.

Commands below are command families. A project may substitute its recorded
equivalent, but the evidence must show the exact executable command and result.

## Gate 1: Input Completeness

- **Prerequisite:** `input/PROJECT_INPUT.md`, `input/project-config.json`, and
  the supplied `input/materials/` set are available; Stage 1 has initialized the
  project.
- **Exact checks:** parse the configuration; validate every required project
  value and enum; confirm every supplied file appears exactly once in
  `content/source-manifest.json`; compare file SHA-256 hashes; identify file
  type, size, and readable page/slide count; explicitly record password-
  protected, corrupt, empty, duplicate, and unsupported files; confirm the
  requested modes and quotas are internally consistent.
- **Evidence artifact:** `reports/INPUT_VALIDATION_REPORT.md` plus the source-
  inventory section of `reports/SOURCE_AUDIT_REPORT.md`.
- **Pass condition:** zero missing required values, zero unmanifested supplied
  files, zero unexplained hash/count mismatch, and every unusable file has a
  stable blocking or review disposition.
- **Failure action:** stop before extraction; correct input/configuration or ask
  the owner for a replacement/decision, update the manifest, and rerun Gate 1.

Example validation and JSON-parsing commands:

```powershell
python -B scripts/validate_project_input.py --input input/PROJECT_INPUT.md --config input/project-config.json --manifest content/source-manifest.json
python -m json.tool input/project-config.json > $null
python -m json.tool content/source-manifest.json > $null
```

## Gate 2: Extraction and Provenance

- **Prerequisite:** Gate 1 passed; Stage 3 extraction and rendering are complete
  for every accepted manifest record.
- **Exact checks:** reconcile manifest page/slide counts with extracted and
  rendered counts; inspect every image-only location and all low-confidence OCR;
  compare a documented sample from every text-based source against its render;
  allow OCR corrections only when visibly supported; verify tool/version,
  source ID, checksum, and location for each extraction chunk; recursively
  validate that every downstream `sourceRef` resolves to a manifest record and
  valid page, slide, section, row, or image; list unreadable locations,
  duplicates, contradictions, and answer-key presence/absence.
- **Evidence artifact:** `reports/SOURCE_AUDIT_REPORT.md`, with source counts,
  total and covered locations, inspection decisions, confidence, corrections,
  unresolved review items, and reviewer/time.
- **Pass condition:** counts reconcile, no accepted location is silently
  skipped, every source-derived record is traceable, and all uncertainty is
  explicitly review-only rather than presented as verified content.
- **Failure action:** block affected chunks; re-extract, rerender, or obtain
  human review/replacement material; invalidate dependent content and rerun the
  complete Gate 2 reference check.

Example Python validator command:

```powershell
python -B scripts/validate_sources.py --manifest content/source-manifest.json --report reports/SOURCE_AUDIT_REPORT.md --check
```

## Gate 3: Canonical Content

- **Prerequisite:** Gate 2 passed and the module/objective map plus canonical
  official-question chunks are complete.
- **Exact checks:** validate schemas and stable ID prefixes; require global ID
  uniqueness and resolvable module/objective/lesson/source links; compare every
  official prompt, option, and marked answer with the visible source; preserve
  every duplicate source reference; verify deterministic duplicate decisions;
  ensure contradictions, missing marks, ambiguous answers, and incomplete
  evidence have `needsReview: true`, are unscored, and are excluded from every
  Mock Exam pool; prove official and generated records cannot share an unlabeled
  identity or origin.
- **Evidence artifact:** `reports/CANONICAL_CONTENT_REPORT.md` and the official-
  question section of `reports/QUESTION_QUALITY_REPORT.md`.
- **Pass condition:** schemas/links/IDs pass, every official answer is visibly
  supported or review-only and unscored, and all source duplicates remain
  traceable.
- **Failure action:** block the affected stable-ID range; correct from visible
  evidence, never inference, then rerun uniqueness, reference, scoring, and
  duplicate checks across the complete canonical set.

Example commands:

```powershell
python -B scripts/validate_content.py --content content --check
Get-ChildItem content -Recurse -Filter *.json | ForEach-Object { python -m json.tool $_.FullName > $null; if ($LASTEXITCODE) { exit $LASTEXITCODE } }
```

## Gate 4: Lessons and Guidance

- **Prerequisite:** Gate 3 mapping checks passed and all intended lesson chunks
  plus generated explanations/guidance have been authored.
- **Exact checks:** reconcile lesson coverage with the source inventory,
  modules, and objectives; require all lesson contract sections and at least one
  valid source reference; verify every generated claim and translation against
  cited evidence; enforce study language and explicit `lang`/`dir`; reject
  unsupported examples, mistakes, or tips; reject empty required content,
  duplicated passages, excessive section length, broken linked-question IDs,
  and undocumented optional-section omissions; verify official content is not
  described as generated and guidance is not described as official.
- **Evidence artifact:** `reports/CONTENT_COVERAGE_REPORT.md` with per-module and
  per-lesson counts, objective coverage, omissions, unsupported-claim results,
  language/direction results, review states, and linked-ID results.
- **Pass condition:** every supported lesson/objective is covered exactly as
  configured, all claims/references/links validate, all required sections meet
  limits, and every omission or shortfall is explicit.
- **Failure action:** return only the affected lesson chunk to authoring or
  review, preserve the stable ID, update its content version, invalidate its old
  approval, and rerun Gate 4 plus affected question checks.

## Gate 5: Generated Questions

- **Prerequisite:** Gate 4 passed for the supporting lessons and generation plus
  independent review are complete for each intended `gq-` chunk.
- **Exact checks:** compare configured targets with achieved counts and explicit
  shortfalls; require objective, difficulty, cognitive level, source references,
  complete claim-level evidence, correct answer, rationale, and review truth-
  table state; apply the complete MCQ and True/False rubrics; reject implausible
  distractors, multiple/no valid answers, answer cues, trivial word flips,
  double negatives, careless absolutes, unsupported facts, semantic duplicates,
  ambiguity, and rationale/answer leakage; verify only approved, scoreable
  generated records enter configured Mock Exam pools.
- **Evidence artifact:** `reports/QUESTION_QUALITY_REPORT.md` with requested and
  achieved counts by type/difficulty/cognitive level/objective, shortfalls,
  evidence/rubric results, duplicate comparisons/dispositions, eligibility, and
  version-bound independent review decisions.
- **Pass condition:** every delivered generated item passes evidence and rubric
  checks, every eligible item has the required approval, no rejected/review item
  is scoreable, and every quota difference is an explicit supported shortfall.
- **Failure action:** reject or return the affected item to authoring; never pad
  quotas with weak content. Increment its content version, clear stale approval,
  rerun duplicate detection over the whole pool, and rerun Gate 5.

## Gate 6: Application Safety and Logic

- **Prerequisite:** Gates 3–5 passed for all delivery content and deterministic
  payload generation/integration is complete.
- **Exact checks:** parse every JSON file; compare schema, stable IDs, references,
  review flags, and payload counts with canonical artifacts; run builders in
  read-only/check mode for byte-identical output; run JavaScript syntax and Node
  tests; prove user/source/generated strings are escaped at rendering boundaries;
  test scoring, deterministic seeded shuffling where promised, search, filters,
  pagination, Practice feedback timing, active-Exam non-leakage, results,
  bookmarks, lesson progress, mistakes, versioned persistence, safe legacy
  normalization, import/export, review-item exclusion, malformed data, and
  optional-guidance failure; check whitespace and unintended changes.
- **Evidence artifact:** `reports/AUTOMATED_QA_REPORT.md`, including commands,
  versions, test totals, payload counts, deterministic diff results, and zero
  unresolved failures.
- **Pass condition:** all validators, parsers, syntax checks, builders, and tests
  exit zero; payload counts/IDs equal the canonical reports; check mode produces
  no diff; no unsafe rendering or exam leakage test fails.
- **Failure action:** stop before browser QA and deployment; add or preserve a
  regression test, repair the canonical source/builder/application as
  appropriate, rebuild deterministically, and rerun Gate 6 in full.

Example command families:

```powershell
python -B -m unittest discover -s scripts -p "test_*.py" -v
Get-ChildItem study-website/data -Recurse -Filter *.json | ForEach-Object { python -m json.tool $_.FullName > $null; if ($LASTEXITCODE) { exit $LASTEXITCODE } }
Get-ChildItem study-website/js -Recurse -Filter *.js | ForEach-Object { node --check $_.FullName; if ($LASTEXITCODE) { exit $LASTEXITCODE } }
node --test study-website/tests/*.test.mjs
python -B scripts/build_payloads.py --check
git diff --check
git diff --exit-code -- study-website/data
```

## Gate 7: Browser QA

- **Prerequisite:** Gate 6 passed for the exact commit; the site is served over
  HTTP from its final static delivery directory, not opened with a `file:` URL.
- **Exact checks:** execute every browser-matrix row and journey below; inspect
  layout, behavior, keyboard/focus, accessible names/landmarks, 44px touch
  targets, contrast, language/direction, persistence, and network requests;
  capture relevant `console.error`, unhandled exception, failed request, mixed-
  content, and CSP errors from a clean load. Third-party browser noise may be
  classified only with the exact message and evidence that it cannot affect the
  site.
- **Evidence artifact:** `reports/BROWSER_QA_REPORT.md` plus screenshots for
  both viewports and traces/screenshots for every failure; summarize the pass in
  `reports/FINAL_QA_REPORT.md`.
- **Pass condition:** every required row and journey passes, there is no
  horizontal overflow, no accessibility blocker, no answer/explanation leak in
  an active exam, and zero relevant console or network errors.
- **Failure action:** stop deployment; record the exact row, route, input state,
  screenshot/trace, and console/network output; repair and rerun the failed row,
  then smoke-test all journeys at both viewports.

Start a local static server in one terminal, wait for the root URL to return
HTTP 200, then run the recorded Playwright projects in a second terminal:

```powershell
python -B -m http.server 8000 --directory study-website
npx playwright test --project=desktop --project=mobile
```

### Required browser matrix

Each row runs on a clean profile and then on imported valid progress. `LTR`
uses an LTR project language and `RTL` uses an RTL project language; changing
only CSS direction without representative content does not pass.

| Row | Viewport | Theme | Direction |
| --- | --- | --- | --- |
| D1 | 1440x1000 | light | LTR |
| D2 | 1440x1000 | dark | LTR |
| D3 | 1440x1000 | light | RTL |
| D4 | 1440x1000 | dark | RTL |
| M1 | 390x844 | light | LTR |
| M2 | 390x844 | dark | LTR |
| M3 | 390x844 | light | RTL |
| M4 | 390x844 | dark | RTL |

For every row, exercise and record:

1. Material index to lesson reading, reading progress, source references, and a
   linked question.
2. Practice answer submission followed by feedback; no feedback appears before
   submission.
3. Mock Exam setup and active Exam non-leakage: no marked answer, correctness,
   rationale, explanation, guidance, or score before submit/expiry.
4. Exam submission to Results and post-submission answer review, including
   scoreable and excluded-item totals.
5. Search with found and zero-result states; combine/reset origin, topic, type,
   and status filters; traverse pagination without lost state.
6. Add/remove lesson and question bookmarks and verify reload persistence.
7. Export progress, reset, import the valid file, reject malformed/wrong-version
   data safely, and verify normalized progress without exam leakage.
8. Keyboard navigation and visible focus, mobile More-menu focus/return,
   responsive navigation, no horizontal overflow, and zero relevant console or
   failed-network errors.

## Gate 8: Deployment

- **Prerequisite:** Gate 7 passed for a committed SHA and the project owner has
  explicitly authorized the remote push/workflow dispatch/publication. A local
  build request, commit request, repository URL, or configured deployment target
  alone is not deployment authorization.
- **Exact checks:** confirm the authorized repository, branch, commit SHA, and
  public URL; ensure the GitHub Pages workflow publishes only the intended
  static folder; push or manually dispatch only as authorized; monitor both
  build and deploy jobs to success; verify the served commit when exposed;
  request public HTML and every required JSON payload and require HTTP 200;
  compare public record counts and stable ID sets with the local verified
  payloads; run public desktop/mobile smoke checks for routes, Material,
  Practice, active-Exam non-leakage, Results, search, filters, bookmarks, and
  progress import/export; require zero relevant console/network errors.
- **Evidence artifact:** `reports/FINAL_QA_REPORT.md` with authorization
  reference, repository/branch/SHA, workflow run URL/ID and conclusions, public
  URL, HTTP evidence, local-versus-public counts, browser matrix subset, time,
  and known limitations.
- **Pass condition:** the authorized workflow build and deploy jobs succeed for
  the verified SHA; public HTML and every required JSON return HTTP 200; public
  counts/IDs equal local counts/IDs; public browser smoke checks pass.
- **Failure action:** do not call the release complete. Diagnose without
  overwriting known-good state; fix through a new reviewed commit or, for a bad
  published commit, use a normal `git revert`, then obtain/confirm authorization
  for the push, monitor the new run, and repeat Gate 8. Never use destructive
  reset or force-push rollback.

Example GitHub Actions, HTTP, and public-count checks:

```powershell
$AuthorizedBranch = "replace-with-authorized-branch"
$RunId = "replace-with-run-id"
gh workflow run pages.yml --ref $AuthorizedBranch
gh run list --workflow pages.yml --branch $AuthorizedBranch --limit 5
gh run watch $RunId --exit-status
$PublicUrl = "https://example.github.io/project/"
(Invoke-WebRequest $PublicUrl).StatusCode
(Invoke-WebRequest "${PublicUrl}data/questions.json").StatusCode
$PublicQuestions = Invoke-RestMethod "${PublicUrl}data/questions.json"
$LocalQuestions = Get-Content -Raw study-website/data/questions.json | ConvertFrom-Json
if ($PublicQuestions.Count -ne $LocalQuestions.Count) { throw "Public question count mismatch" }
npx playwright test --config playwright.public.config.mjs --project=desktop --project=mobile
```

The `gh workflow run` line is an external mutation: show it in the plan, but do
not execute it without explicit deployment authorization. Monitoring and public
verification never convert absent authorization into permission to publish.
