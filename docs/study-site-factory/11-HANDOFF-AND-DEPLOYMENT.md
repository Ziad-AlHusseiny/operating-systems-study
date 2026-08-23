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
| `reports/FINAL_HANDOFF_EVIDENCE.json` | Machine-readable counts, review items, test evidence, and limitations used by the final handoff. | Generate from the canonical reports in Stage 11, validate it, and commit it with the release. |
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

The following commit-bound dispatch and monitoring commands are safe only after
a separately authorized publish action. They compute the full expected SHA,
prove the configured remote branch points to it, snapshot existing dispatches,
and derive the new run ID rather than accepting one manually:

```powershell
$ProjectConfig = Get-Content -Raw input/project-config.json | ConvertFrom-Json
$ConfiguredRepository = [string]$ProjectConfig.deployment.repository
$AuthorizedBranch = [string]$ProjectConfig.deployment.branch
$ActualRepository = (gh repo view --json nameWithOwner --jq .nameWithOwner).Trim()
if ($ActualRepository -ne $ConfiguredRepository) { throw "Configured repository does not match the current gh repository" }

$ExpectedSha = (git rev-parse HEAD).Trim().ToLowerInvariant()
if ($ExpectedSha -notmatch "^[0-9a-f]{40}$") { throw "Expected SHA is not a full commit SHA" }
$RemoteRef = @(git ls-remote --heads origin "refs/heads/$AuthorizedBranch")
if ($LASTEXITCODE -ne 0 -or $RemoteRef.Count -ne 1) { throw "Authorized remote branch was not found exactly once" }
$RemoteSha = (($RemoteRef[0] -split "\s+")[0]).ToLowerInvariant()
if ($RemoteSha -ne $ExpectedSha) { throw "Authorized remote branch is not at the Gate-7-approved commit" }

$ExistingRuns = @(gh run list --workflow pages.yml --branch $AuthorizedBranch --event workflow_dispatch --limit 100 --json databaseId,headSha | ConvertFrom-Json)
if ($LASTEXITCODE -ne 0) { throw "Could not snapshot existing workflow runs" }
$ExistingRunIds = @($ExistingRuns | ForEach-Object { [string]$_.databaseId })
gh workflow run pages.yml --ref $AuthorizedBranch
if ($LASTEXITCODE -ne 0) { throw "Workflow dispatch failed" }

$RunId = $null
$RunDeadline = (Get-Date).AddMinutes(2)
do {
    $CandidateRuns = @(gh run list --workflow pages.yml --branch $AuthorizedBranch --event workflow_dispatch --limit 100 --json databaseId,headSha | ConvertFrom-Json | Where-Object {
        $_.headSha -eq $ExpectedSha -and [string]$_.databaseId -notin $ExistingRunIds
    })
    if ($LASTEXITCODE -ne 0) { throw "Could not query the dispatched workflow run" }
    if ($CandidateRuns.Count -gt 1) { throw "More than one new workflow run matches the approved commit" }
    if ($CandidateRuns.Count -eq 1) { $RunId = [string]$CandidateRuns[0].databaseId; break }
    Start-Sleep -Seconds 3
} while ((Get-Date) -lt $RunDeadline)
if ([string]::IsNullOrWhiteSpace($RunId)) { throw "No new workflow-dispatch run matched the approved commit" }

gh run watch $RunId --exit-status
if ($LASTEXITCODE -ne 0) { throw "Workflow run failed" }
$Run = gh run view $RunId --json headSha,conclusion,jobs | ConvertFrom-Json
if ($LASTEXITCODE -ne 0) { throw "Could not read workflow run evidence" }
if ($Run.headSha -ne $ExpectedSha) { throw "Workflow run used a different commit" }
if ($Run.conclusion -ne "success") { throw "Workflow conclusion was not success" }
$RequiredJobs = @("build", "deploy")
foreach ($JobName in $RequiredJobs) {
    $MatchingJobs = @($Run.jobs | Where-Object { $_.name -eq $JobName })
    if ($MatchingJobs.Count -ne 1 -or $MatchingJobs[0].conclusion -ne "success") {
        throw "Required workflow job did not succeed: $JobName"
    }
}
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

The read-only verification below checks HTML separately, then discovers every
JSON file that the final static data directory publishes. It fails on status,
content type, parsing, record-count, or stable-ID parity rather than checking a
single named payload:

```powershell
$ProjectConfig = Get-Content -Raw input/project-config.json | ConvertFrom-Json
$PublicUrl = ([string]$ProjectConfig.deployment.publicUrl).TrimEnd("/") + "/"

function Get-PayloadRecords {
    param([object]$Payload, [string]$PayloadName)
    if ($Payload -is [System.Array]) { $Payload; return }
    $FoundCollection = $false
    foreach ($Collection in $Payload.PSObject.Properties) {
        $Value = $Collection.Value
        if ($Value -is [System.Array]) {
            $FoundCollection = $true
            foreach ($Record in @($Value)) { $Record }
            continue
        }
        if ($Value -is [System.Management.Automation.PSCustomObject]) {
            $MapEntries = @($Value.PSObject.Properties | Where-Object {
                $_.Name -match "^(?:source|module|objective|lesson|q|gq)-.+$"
            })
            $MapPropertyCount = @($Value.PSObject.Properties).Count
            if ($MapEntries.Count -gt 0 -and $MapEntries.Count -eq $MapPropertyCount) {
                $FoundCollection = $true
                foreach ($Entry in $MapEntries) {
                    [pscustomobject]@{ "__stableId" = $Entry.Name; "__record" = $Entry.Value }
                }
            }
        }
    }
    if (-not $FoundCollection) { throw "$PayloadName has no supported top-level record collection" }
}

function Get-StableId {
    param([object]$Record, [string]$PayloadName)
    foreach ($Field in @("__stableId", "id", "sourceId", "questionId", "lessonId", "moduleId", "objectiveId")) {
        $Property = $Record.PSObject.Properties[$Field]
        if ($null -ne $Property -and -not [string]::IsNullOrWhiteSpace([string]$Property.Value)) {
            return [string]$Property.Value
        }
    }
    throw "$PayloadName contains a record without a stable ID"
}

$HtmlResponse = Invoke-WebRequest -Uri $PublicUrl
if ($HtmlResponse.StatusCode -ne 200) { throw "Public HTML did not return HTTP 200" }
$HtmlContentType = [string]$HtmlResponse.Headers["Content-Type"]
if ($HtmlContentType -notmatch "(?i)^text/html(?:\s*;|$)") { throw "Public root is not HTML" }

$DataRoot = (Resolve-Path study-website/data).Path
$RequiredPayloads = @(Get-ChildItem $DataRoot -Recurse -Filter *.json -File)
if ($RequiredPayloads.Count -eq 0) { throw "No required published JSON payloads were found" }
foreach ($LocalFile in $RequiredPayloads) {
    $RelativePath = [IO.Path]::GetRelativePath($DataRoot, $LocalFile.FullName).Replace("\", "/")
    $PayloadUrl = [Uri]::new([Uri]$PublicUrl, "data/$RelativePath").AbsoluteUri
    $Response = Invoke-WebRequest -Uri $PayloadUrl
    if ($Response.StatusCode -ne 200) { throw "$RelativePath did not return HTTP 200" }
    $ContentType = [string]$Response.Headers["Content-Type"]
    if ($ContentType -notmatch "(?i)^application/(?:[a-z0-9.+-]+\+)?json(?:\s*;|$)") {
        throw "$RelativePath did not return a JSON content type"
    }
    try {
        $LocalPayload = Get-Content -Raw $LocalFile.FullName | ConvertFrom-Json -Depth 100 -NoEnumerate
        $PublicPayload = $Response.Content | ConvertFrom-Json -Depth 100 -NoEnumerate
    } catch { throw "$RelativePath could not be parsed as JSON: $($_.Exception.Message)" }
    $LocalRecords = @(Get-PayloadRecords $LocalPayload $RelativePath)
    $PublicRecords = @(Get-PayloadRecords $PublicPayload $RelativePath)
    if ($PublicRecords.Count -ne $LocalRecords.Count) { throw "$RelativePath record count mismatch" }
    $LocalIds = @($LocalRecords | ForEach-Object { Get-StableId $_ $RelativePath } | Sort-Object)
    $PublicIds = @($PublicRecords | ForEach-Object { Get-StableId $_ $RelativePath } | Sort-Object)
    if (@(Compare-Object $LocalIds $PublicIds).Count -ne 0) { throw "$RelativePath stable-ID mismatch" }
}
```

## Non-destructive rollback

Rollback creates a normal auditable commit; never use `git reset --hard`, branch
rewriting, or force push. First preserve evidence and identify the exact bad
published commit and the last known-good public commit. Then:

```powershell
# Precondition: HEAD is the exact bad published commit recorded in FINAL_QA_REPORT.md.
$RollbackSha = (git rev-parse HEAD).Trim().ToLowerInvariant()
if ($RollbackSha -notmatch "^[0-9a-f]{40}$") { throw "Rollback SHA is not a full commit SHA" }
git show --no-patch --format=fuller $RollbackSha
git revert $RollbackSha
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

The final message and `reports/FINAL_QA_REPORT.md` must include every field.
Stage 11 must generate and commit `reports/FINAL_HANDOFF_EVIDENCE.json` from
`SOURCE_AUDIT_REPORT.md`, `CONTENT_COVERAGE_REPORT.md`,
`QUESTION_QUALITY_REPORT.md`, and `FINAL_QA_REPORT.md`. Its schema is exact:

| Field | Type and rule |
| --- | --- |
| `schemaVersion` | Integer `1`. |
| `counts` | Object with exactly non-negative integer `sources`, `lessons`, `official`, `generatedMcq`, `generatedTrueFalse`, `explanations`, and `reviewItems`. |
| `reviewItems` | Array of exact objects with non-empty `id`, `location`, `disposition`, and `owner`; its length equals `counts.reviewItems`. |
| `tests` | Non-empty array of exact objects with non-empty `command`, `toolVersion`, and repository-relative `evidence`, plus non-negative integer `passed` and integer `failed` equal to zero. |
| `knownLimitations` | Array of exact objects with non-empty `description`, `impact`, and `workaround`; use an empty array when none exist. |

The following block is self-contained. It refuses missing, untracked, modified,
malformed, failed, or commit-mismatched evidence before formatting the handoff:

```powershell
$DeploymentVerified = $false
$EvidencePath = "reports/FINAL_HANDOFF_EVIDENCE.json"
$RequiredEvidence = @(
    "reports/SOURCE_AUDIT_REPORT.md",
    "reports/CONTENT_COVERAGE_REPORT.md",
    "reports/QUESTION_QUALITY_REPORT.md",
    "reports/FINAL_QA_REPORT.md",
    $EvidencePath
)
foreach ($Path in $RequiredEvidence) {
    if (-not (Test-Path -LiteralPath $Path -PathType Leaf)) { throw "Required handoff evidence is missing: $Path" }
    git ls-files --error-unmatch -- $Path *> $null
    if ($LASTEXITCODE -ne 0) { throw "Required handoff evidence is not committed: $Path" }
    git diff --quiet -- $Path
    if ($LASTEXITCODE -ne 0) { throw "Required handoff evidence differs from the committed release: $Path" }
}

function Assert-ExactProperties {
    param([object]$Object, [string[]]$Expected, [string]$Path)
    if ($null -eq $Object) { throw "$Path is missing" }
    $Actual = @($Object.PSObject.Properties.Name | Sort-Object)
    $ExpectedSorted = @($Expected | Sort-Object)
    if (@(Compare-Object $ExpectedSorted $Actual).Count -ne 0) { throw "$Path has an invalid field set" }
}

$Evidence = Get-Content -Raw $EvidencePath | ConvertFrom-Json -Depth 100
Assert-ExactProperties $Evidence @("schemaVersion", "counts", "reviewItems", "tests", "knownLimitations") "handoff evidence"
if ($Evidence.schemaVersion -ne 1) { throw "Unsupported handoff evidence schemaVersion" }

$CountFields = @("sources", "lessons", "official", "generatedMcq", "generatedTrueFalse", "explanations", "reviewItems")
Assert-ExactProperties $Evidence.counts $CountFields "handoff evidence counts"
foreach ($Field in $CountFields) {
    $Value = $Evidence.counts.PSObject.Properties[$Field].Value
    if (($Value -isnot [int] -and $Value -isnot [long]) -or $Value -lt 0) { throw "Invalid non-negative integer count: $Field" }
}
$CountsSummary = "sources=$($Evidence.counts.sources), lessons=$($Evidence.counts.lessons), official=$($Evidence.counts.official), generated-mcq=$($Evidence.counts.generatedMcq), generated-true-false=$($Evidence.counts.generatedTrueFalse), explanations=$($Evidence.counts.explanations), review-items=$($Evidence.counts.reviewItems)"

$ReviewItems = @($Evidence.reviewItems)
if ($ReviewItems.Count -ne $Evidence.counts.reviewItems) { throw "Review-item count does not match evidence counts" }
foreach ($Item in $ReviewItems) {
    Assert-ExactProperties $Item @("id", "location", "disposition", "owner") "review item"
    foreach ($Field in @("id", "location", "disposition", "owner")) {
        if ([string]::IsNullOrWhiteSpace([string]$Item.PSObject.Properties[$Field].Value)) { throw "Review item has an empty field: $Field" }
    }
}
$ReviewItemSummary = if ($ReviewItems.Count -eq 0) { "none" } else {
    (@($ReviewItems | ForEach-Object { "$($_.id) at $($_.location); $($_.disposition); owner=$($_.owner)" }) -join " | ")
}

$Tests = @($Evidence.tests)
if ($Tests.Count -eq 0) { throw "Handoff test evidence is empty" }
foreach ($Test in $Tests) {
    Assert-ExactProperties $Test @("command", "toolVersion", "passed", "failed", "evidence") "test evidence"
    foreach ($Field in @("command", "toolVersion", "evidence")) {
        if ([string]::IsNullOrWhiteSpace([string]$Test.PSObject.Properties[$Field].Value)) { throw "Test evidence has an empty field: $Field" }
    }
    if (($Test.passed -isnot [int] -and $Test.passed -isnot [long]) -or $Test.passed -lt 0) { throw "Test passed count is invalid" }
    if (($Test.failed -isnot [int] -and $Test.failed -isnot [long]) -or $Test.failed -ne 0) { throw "Test evidence contains failures" }
    if (-not (Test-Path -LiteralPath $Test.evidence -PathType Leaf)) { throw "Named test evidence is missing: $($Test.evidence)" }
    git ls-files --error-unmatch -- $Test.evidence *> $null
    if ($LASTEXITCODE -ne 0) { throw "Named test evidence is not committed: $($Test.evidence)" }
    git diff --quiet -- $Test.evidence
    if ($LASTEXITCODE -ne 0) { throw "Named test evidence differs from the committed release: $($Test.evidence)" }
}
$TestSummary = @($Tests | ForEach-Object { "$($_.command) [$($_.toolVersion)]: passed=$($_.passed), failed=$($_.failed), evidence=$($_.evidence)" }) -join " | "

$KnownLimitations = @($Evidence.knownLimitations)
foreach ($Limitation in $KnownLimitations) {
    Assert-ExactProperties $Limitation @("description", "impact", "workaround") "known limitation"
    foreach ($Field in @("description", "impact", "workaround")) {
        if ([string]::IsNullOrWhiteSpace([string]$Limitation.PSObject.Properties[$Field].Value)) { throw "Known limitation has an empty field: $Field" }
    }
}
$KnownLimitationsSummary = if ($KnownLimitations.Count -eq 0) { "none" } else {
    (@($KnownLimitations | ForEach-Object { "$($_.description); impact=$($_.impact); workaround=$($_.workaround)" }) -join " | ")
}

$ProjectConfig = Get-Content -Raw input/project-config.json | ConvertFrom-Json
$Repository = [string]$ProjectConfig.deployment.repository
$Branch = [string]$ProjectConfig.deployment.branch
$PublicUrl = ([string]$ProjectConfig.deployment.publicUrl).TrimEnd("/") + "/"
$Commit = (git rev-parse HEAD).Trim().ToLowerInvariant()
if ($Commit -notmatch "^[0-9a-f]{40}$") { throw "Release commit is not a full SHA" }
$MatchingRuns = @(gh run list --workflow pages.yml --branch $Branch --event workflow_dispatch --commit $Commit --status success --limit 20 --json databaseId,headSha,conclusion,createdAt | ConvertFrom-Json | Where-Object {
    $_.headSha -eq $Commit -and $_.conclusion -eq "success"
} | Sort-Object createdAt -Descending)
if ($LASTEXITCODE -ne 0) { throw "Could not query Pages runs for the committed release" }
$RunId = $null
$Run = $null
if ($MatchingRuns.Count -gt 0) {
    $RemoteRef = @(git ls-remote --heads origin "refs/heads/$Branch")
    if ($LASTEXITCODE -ne 0 -or $RemoteRef.Count -ne 1) { throw "Configured remote branch was not found exactly once" }
    $RemoteSha = (($RemoteRef[0] -split "\s+")[0]).ToLowerInvariant()
    if ($RemoteSha -ne $Commit) { throw "Configured remote branch is not at the committed release" }
    $RunId = [string]$MatchingRuns[0].databaseId
    $Run = gh run view $RunId --json headSha,conclusion,jobs | ConvertFrom-Json
    if ($LASTEXITCODE -ne 0 -or $Run.headSha -ne $Commit -or $Run.conclusion -ne "success") { throw "Pages run does not verify the committed release" }
    foreach ($JobName in @("build", "deploy")) {
        $Jobs = @($Run.jobs | Where-Object { $_.name -eq $JobName -and $_.conclusion -eq "success" })
        if ($Jobs.Count -ne 1) { throw "Required Pages job did not succeed: $JobName" }
    }
    $HtmlResponse = Invoke-WebRequest -Uri $PublicUrl
    if ($HtmlResponse.StatusCode -ne 200 -or [string]$HtmlResponse.Headers["Content-Type"] -notmatch "(?i)^text/html(?:\s*;|$)") { throw "Public release HTML verification failed" }
    $DeploymentVerified = $true
}

$VerifiedUrl = if ($DeploymentVerified) { $PublicUrl } else { "not deployed" }
$WorkflowRunSummary = if ($DeploymentVerified) {
    "run $RunId; commit $($Run.headSha); build/deploy success"
} else {
    "not run — awaiting explicit authorization"
}
$HandoffSummary = @"
Repository: $Repository
Branch: $Branch
Commit: $Commit
Public URL: $VerifiedUrl
Counts: $CountsSummary
Review items: $ReviewItemSummary
Tests: $TestSummary
Workflow run: $WorkflowRunSummary
Known limitations: $KnownLimitationsSummary
"@
```

Also state whether the worktree was clean, whether deterministic check mode
produced no diff, which progress-schema versions are supported, and where the
source audit, coverage, question-quality, browser, and final QA evidence live.
Do not call a URL verified when public verification did not run.
