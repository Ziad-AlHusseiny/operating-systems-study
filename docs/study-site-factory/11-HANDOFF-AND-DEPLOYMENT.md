# Maintainer handoff and deployment

Handoff transfers a reproducible, already-verified static site and its canonical
content. Deployment is a separate, externally mutating action. Preparing or
committing the handoff does not authorize a push, GitHub Actions dispatch, or
publication.

## Maintainer file map

| Path | Maintainer purpose | Editing rule |
| --- | --- | --- |
| `input/PROJECT_INPUT.md` | Human-approved scope, languages, branding, and publication destination. | Edit decisions here, then invalidate dependent stages. |
| `input/project-config.json` | Machine-readable quotas, modes, exam defaults, persistence version, and deployment settings. | Validate after every edit; do not override it only in generated files. |
| `input/materials/` | Original supplied evidence. | Preserve originals; additions/replacements require a new manifest hash and source audit. |
| `content/source-manifest.json` | Stable `source-` inventory, hashes, formats, and locations. | Rebuild from inputs; retain stable IDs where identity is unchanged. |
| `content/lessons/` | Canonical generated lesson records. | Edit canonical records with evidence/review metadata, then rebuild delivery payloads. |
| `content/official-questions/` | Faithful source-derived questions and marked answers. | Correct only from visible source evidence and retain all source references. |
| `content/generated-questions/` | Generated practice items, evidence, rubric state, and approval. | A content edit increments the version and invalidates the old approval. |
| `content/explanations/` | Clearly labeled generated study guidance. | Keep separate from official answers and preserve evidence/review fields. |
| `scripts/` | Validators, deterministic builders, migrations, and tests. | Change with tests; record runtime/tool versions. |
| `reports/` | Source audit, coverage, question quality, QA, and review evidence. | Append or regenerate from evidence; never hide a failure or review item. |
| `progress-ledger.md` | Stage/chunk hashes, validation, open reviews, and resume point. | Preserve history; invalidate from the earliest affected stage. |
| `study-website/` | Final static application, generated data, assets, tests, and operating README. | Edit authored UI source when appropriate; do not hand-edit generated payloads. |
| `.github/workflows/pages.yml` | GitHub Pages validation, artifact upload, and deployment. | Review permissions, branch trigger, source directory, and manual dispatch before use. |

The handoff identifies which files are canonical inputs, authored application
files, deterministic outputs, and evidence. If a project uses different paths,
record a complete equivalent map in `study-website/README.md` and
`reports/FINAL_QA_REPORT.md`.

## Safe content corrections

### Source-derived content

For source manifests and official questions, open the cited original and its
render. Correct transcription, normalization, or a marked answer only when the
visible page/slide/section supports the change. Preserve original source files,
stable IDs, duplicate source references, and the audit trail. If sources
conflict, the mark is missing, or the render is unreadable, set the record to
review-only and unscored, add an exact review note, and request a human decision.
Do not infer an official answer from a generated lesson, rationale, outside
knowledge, or what appears likely.

### Generated content

Edit generated lessons, questions, and guidance in `content/`, not in the
delivery JSON. Retain claim-level evidence and generated labels. Re-run the
applicable lesson/question rubric and duplicate checks. Any semantic edit
increments `contentVersion`; clear the old version-bound approval and restore
the appropriate unreviewed or needs-review state until independent review is
complete. A generated item cannot be called official.

### Review-item correction

Locate the stable review ID in `SOURCE_AUDIT_REPORT.md`,
`CONTENT_COVERAGE_REPORT.md`, or `QUESTION_QUALITY_REPORT.md`; inspect its cited
evidence; record the reviewer, decision, reason, time, record ID, and content
version. If evidence remains insufficient, keep the item visibly labeled,
unscored, and excluded from Mock Exams. `unknown` or `needs-review` is a valid
safe outcome; guessing is not.

## Deterministic rebuild and read-only checks

Record the exact project commands and pinned runtime versions in the final
report. The standard command families are:

```powershell
# Rebuild delivery JSON from canonical content.
python -B scripts/build_payloads.py

# Prove a clean tree would produce byte-identical payloads without writing.
python -B scripts/build_payloads.py --check
git diff --exit-code -- study-website/data

# Validate canonical content and parse every delivery payload.
python -B scripts/validate_content.py --content content --check
Get-ChildItem study-website/data -Recurse -Filter *.json | ForEach-Object { python -m json.tool $_.FullName > $null; if ($LASTEXITCODE) { exit $LASTEXITCODE } }

# Run application checks without publishing.
python -B -m unittest discover -s scripts -p "test_*.py" -v
Get-ChildItem study-website/js -Recurse -Filter *.js | ForEach-Object { node --check $_.FullName; if ($LASTEXITCODE) { exit $LASTEXITCODE } }
node --test study-website/tests/*.test.mjs
git diff --check
```

If the generated project names a script differently, replace the example with
the actual checked-in command before handoff. A rebuild is acceptable only when
the canonical input hashes and tool versions are recorded, builders use stable
ID ordering and fixed serialization, repeated runs are byte-identical, and
`--check` is read-only. Never fix a generated JSON file manually; fix its
canonical input or builder and rebuild.

## Versioned progress migration

Persisted progress includes an explicit schema version. When content IDs,
review flags, scoring eligibility, or storage shape changes:

1. Increment the configured progress schema version and add a deterministic
   migration from every supported prior version.
2. Parse imported/local data as untrusted input; reject malformed structure and
   unsupported future versions without overwriting the user's valid state.
3. Keep only IDs present in current canonical payloads. Normalize attempts,
   mistakes, results, and exam sessions against current scoreability and review
   flags; never restore pre-submit feedback into an active exam.
4. Preserve compatible lesson progress, bookmarks, and preferences. Report
   dropped or changed records to the user without inventing replacements.
5. Test empty, current, each supported legacy, malformed, unknown-ID, changed-
   eligibility, and interrupted-exam fixtures. Verify export followed by import
   is stable for the current version.

Do not silently clear all user progress as a migration. If safe migration is
impossible, preserve the original export, explain the incompatibility, and ask
before reset.

## GitHub Pages workflow contract

The checked-in `.github/workflows/pages.yml` must use least-privilege
permissions, validate the intended commit, upload only the final static
`study-website/` folder, and deploy that artifact. It normally triggers on a
push to the configured publication branch and also exposes
`workflow_dispatch` for an authorized manual run. The build/test job must finish
before the deploy job; concurrency must prevent an older in-flight run from
overwriting the intended release. The static artifact must not include original
source materials, temporary OCR files, secrets, dependency folders, or reports
that were not approved for publication.

Before a manual dispatch, verify the repository, workflow, branch, commit,
environment, Pages base path, and artifact directory. Record the resulting run
ID/URL and both build and deploy conclusions. A successful workflow for the
wrong SHA or folder is a failed release.

## Deployment authorization boundary

Explicit authorization must identify, or unambiguously apply to, the target
repository and this deployment action. Authorization to create files, run
tests, make a local commit, prepare a release, or inspect a public site does not
authorize any of these external mutations:

- pushing a commit or tag;
- running `gh workflow run` or re-running a GitHub Actions job;
- enabling/changing GitHub Pages, branch protections, permissions, DNS, or a
  hosting environment;
- publishing or replacing the public artifact.

If explicit deployment authorization is absent, stop after the verified local
commit and handoff. Record `Deployment: not run — awaiting explicit
authorization`, provide the exact proposed repository/branch/SHA/workflow, and
ask the owner. Do not interpret silence, a configured URL, prior authorization
for a different SHA, or the existence of an automatic workflow as permission.

When authorization is present, confirm that it still covers any repair or
rollback push. Never expose credentials or place tokens in commands, reports,
payloads, or browser artifacts.

## Authorized deployment procedure

1. Confirm a clean worktree and record the exact Gate-7-approved commit SHA.
2. Re-run the complete local automated gate and the two-viewport browser smoke
   against that SHA; append fresh evidence to `FINAL_QA_REPORT.md`.
3. Confirm the authorized repository, branch, workflow, static folder, and
   public URL. Show any external mutation before running it.
4. Push the exact commit or dispatch `.github/workflows/pages.yml` only within
   the authorization. Do not force-push.
5. Monitor the run until both build and deploy jobs conclude `success`; record
   the workflow run ID/URL, deployed SHA, and times.
6. Complete every public check below. A workflow success alone is insufficient.

Typical monitoring commands, safe after a separately authorized publish action,
are:

```powershell
$AuthorizedBranch = "replace-with-authorized-branch"
$RunId = "replace-with-run-id"
gh run list --workflow pages.yml --branch $AuthorizedBranch --limit 5
gh run watch $RunId --exit-status
gh run view $RunId
```

## Public verification

Use a cache-busting query or clean browser profile and verify the expected base
path. Save URL, status, content type, count/ID comparison, time, and result for
each check.

1. Request the public root HTML and every required JSON payload. Require HTTP
   200, correct content types, and parseable content; reject a host's branded
   HTML error page returned under a misleading status/content path.
2. Compare public counts and stable ID sets for sources, lessons, official
   questions, generated questions, explanations, and review items with the
   local verified reports and payloads.
3. In public browsers at 1440x1000 and 390x844, smoke Dashboard, Material
   reading, Practice feedback, active-Exam non-leakage, Results, search,
   combined filters, pagination, bookmarks, and progress export/import.
4. Check light/dark and at least the configured LTR/RTL direction, responsive
   navigation, asset/base-path loading, no horizontal overflow, and zero
   relevant console exceptions or failed network requests.

Example read-only HTTP and count checks:

```powershell
$PublicUrl = "https://example.github.io/project/"
$RootResponse = Invoke-WebRequest $PublicUrl
if ($RootResponse.StatusCode -ne 200 -or $RootResponse.Content -notmatch "<html") { throw "Public HTML verification failed" }
$PublicQuestions = Invoke-RestMethod "${PublicUrl}data/questions.json"
$LocalQuestions = Get-Content -Raw study-website/data/questions.json | ConvertFrom-Json
if ($PublicQuestions.Count -ne $LocalQuestions.Count) { throw "Public question count mismatch" }
```

## Non-destructive rollback

Rollback creates a normal auditable commit; never use `git reset --hard`, branch
rewriting, or force push. First preserve evidence and identify the exact bad
published commit and the last known-good public commit. Then:

```powershell
$BadCommitSha = "replace-with-bad-commit-sha"
git revert $BadCommitSha
python -B -m unittest discover -s scripts -p "test_*.py" -v
node --test study-website/tests/*.test.mjs
git diff --check HEAD^ HEAD
```

Review the revert, run Gates 6 and 7, and obtain or confirm authorization before
pushing the revert commit. Monitor the new Pages workflow and rerun all Gate 8
HTTP, payload-count, and public browser checks. If reverting a merge or a range
needs special mainline/order selection, stop and have the maintainer approve the
specific revert plan; do not guess. The failed deployment and rollback evidence
remain in `FINAL_QA_REPORT.md`.

## Final handoff summary

The final message and `reports/FINAL_QA_REPORT.md` must include every field:

```text
Repository: <owner/name>
Branch: <verified branch>
Commit: <full SHA tested and, if authorized, deployed>
Public URL: <verified URL or not deployed>
Counts: sources=<n>, lessons=<n>, official=<n>, generated-mcq=<n>, generated-true-false=<n>, explanations=<n>, review-items=<n>
Review items: <stable IDs, locations, disposition, owner; or none>
Tests: <exact commands, tool versions, pass/fail totals, evidence paths>
Workflow run: <run ID/URL and build/deploy conclusions; or not run — awaiting explicit authorization>
Known limitations: <specific impact and workaround; or none>
```

Also state whether the worktree was clean, whether deterministic check mode
produced no diff, which progress-schema versions are supported, and where the
source audit, coverage, question-quality, browser, and final QA evidence live.
Do not call a URL verified when public verification did not run.
