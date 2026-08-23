# Master build prompt

Build a reusable, source-backed static study and exam website in the current
repository. Use the current static study-site repository as the UI
implementation base; preserve its proven architecture and replace only the
project-specific content, configuration, branding, and necessary UI details.

## Start and validate

1. Read `input/PROJECT_INPUT.md` and `input/project-config.json` first, then
   inventory every file under `input/materials/`. Treat these as the first three
   project inputs.
2. Validate the minimum inputs before acting: project identity, source and study
   languages, one content-policy mode, material inventory, official-answer-key
   policy, question targets, exam defaults, review policy, and intended
   deployment destination. Run Gate 1 from
   [09-QA-GATES.md](09-QA-GATES.md). If a required value or material decision is
   missing, record the exact blocker and stop the dependent work.
3. Copy the project values into the contracts defined by
   [01-PROJECT-INPUT-TEMPLATE.md](01-PROJECT-INPUT-TEMPLATE.md),
   [02-PRD-TEMPLATE.md](02-PRD-TEMPLATE.md), and
   [examples/project-config.example.json](examples/project-config.example.json).
   Do not import course-specific content from the current example study site.

## Execute the active stage

Follow [08-BUILD-WORKFLOW.md](08-BUILD-WORKFLOW.md) in order. At each stage,
read only the numbered document for the active work plus the shared
[04-CONTENT-AND-DATA-CONTRACTS.md](04-CONTENT-AND-DATA-CONTRACTS.md) and the
applicable gate in [09-QA-GATES.md](09-QA-GATES.md). Use
[03-SOURCE-INGESTION-SPEC.md](03-SOURCE-INGESTION-SPEC.md) for source work,
[05-MATERIAL-LESSONS-SPEC.md](05-MATERIAL-LESSONS-SPEC.md) for lessons,
[06-QUESTION-GENERATION-SPEC.md](06-QUESTION-GENERATION-SPEC.md) for generated
questions, [07-UX-AND-SYSTEM-FLOW.md](07-UX-AND-SYSTEM-FLOW.md) for application
integration, and
[11-HANDOFF-AND-DEPLOYMENT.md](11-HANDOFF-AND-DEPLOYMENT.md) for release and
handoff.

For every stage:

1. Keep `progress-ledger.md` with the stage, stable chunk ID, input and output
   SHA-256 hashes, validation result, open review IDs, and next stage. Reuse a
   completed artifact only when its recorded inputs and content hashes still
   match; invalidate the smallest affected downstream chunks when they do not.
2. Inventory every supplied source. Use source-appropriate extraction for PDF,
   DOCX, PPTX, text/Markdown, CSV/JSON, and images. Render and visually inspect
   the locations required by the ingestion specification, especially OCR,
   diagrams, tables, questions, marked answers, and low-confidence output.
3. Preserve stable IDs and exact source locations. Keep official source
   content, labeled generated content, and unresolved review content in
   separate canonical states and pools. Never allow official and generated
   records to share an unlabeled pool.
4. Build Material lessons with the required objectives, summary, explanation,
   key terms, supported worked examples, supported common mistakes, supported
   exam tips, recap, source references, review state, and linked questions.
5. Build exam-quality MCQ and True/False questions only from supported evidence.
   Apply the complete rubrics, quotas, claim-level evidence, difficulty,
   objective, rationale, duplicate, version-bound review, and scoring rules in
   the question and data contracts. Report supported quota shortfalls instead
   of padding a pool.
6. Stop at unresolved, missing, unreadable, conflicting, or ambiguous evidence.
   Create a traceable review item and exclude it from scoreable use; never guess
   an official answer or unsupported generated claim.
7. Build delivery payloads deterministically from canonical content, integrate
   them into the existing static site, and do not hand-edit generated payloads.
8. Run every blocking gate for the stage. Save the named evidence artifact,
   repair each failure at its canonical source, rerun invalidated checks, and
   continue only after the gate's pass condition is met.

## Low-token operating mode

- Read stage-scoped instructions only: the active numbered document, the shared
  data contracts, and the applicable QA gate.
- Work in stable module, lesson, source-location, or inclusive stable-ID chunks;
  keep chunk boundaries unchanged across retries.
- Reuse validated artifacts and ledger evidence when recorded hashes match.
- Do not repeat the product explanation, fixed architecture, or completed-stage
  summaries in each status message; reference the recorded artifact instead.
- Use deterministic builders, stable-ID ordering, fixed serialization, and
  read-only check modes so identical inputs produce byte-identical output.
- Keep status updates concise: active stage/chunk, completed evidence, blocker or
  gate result, and next action.

## Finish and deployment boundary

Run every remaining blocking validator, JSON parse, syntax check, automated
test, deterministic rebuild check, whitespace check, and browser QA row. Repair
all failures and bind the evidence to the exact committed SHA.

Do not push, dispatch a workflow, change hosting, or publish unless the project
owner has explicitly authorized deployment for the target repository and this
release action. If authorization was not already given, finish the verified
local commit, record `Deployment: not run — awaiting explicit authorization`,
show the proposed repository, branch, SHA, workflow, and public URL, and request
deployment authorization. A repository URL, configured target, local build, or
commit request is not authorization.

Finish with a concise handoff containing the repository and branch, exact commit
SHA, public URL or the awaiting-authorization state, source and lesson counts,
official and generated question counts by type, explanation and review-item
counts, unresolved review items and known limitations, and every test command,
tool version, pass/fail total, and committed evidence path.
