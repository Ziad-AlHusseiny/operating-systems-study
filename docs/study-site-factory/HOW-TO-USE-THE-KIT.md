# How to use the study-site factory kit

Use this guide when you want to build a new study website from different
course materials while keeping the same product flow and quality rules.

## What you need

Prepare:

- A new Git project folder.
- Your PDF, DOCX, PPTX, text, Markdown, CSV, JSON, or image files.
- Any official question bank and answer key you have.
- The course title, study language, branding, and GitHub repository details.
- Codex opened at the root of the new project.

## Step 1: Copy the factory files

Copy these items into the new project without changing their internal paths:

```text
docs/study-site-factory/
scripts/validate_factory_kit.py
scripts/test_validate_factory_kit.py
```

Your new project should start with this structure:

```text
new-study-project/
├── docs/
│   └── study-site-factory/
├── input/
│   ├── PROJECT_INPUT.md
│   ├── project-config.json
│   └── materials/
└── scripts/
    ├── validate_factory_kit.py
    └── test_validate_factory_kit.py
```

## Step 2: Add the course materials

Put every source file inside `input/materials/`.

Keep the original filenames. Include answer keys and question banks as
separate files. Do not remove difficult, unclear, or contradictory pages; the
workflow records them as review items instead of silently skipping them.

Example:

```text
input/materials/
├── course-book.pdf
├── lecture-slides.pptx
├── official-questions.pdf
└── answer-key.pdf
```

## Step 3: Complete the project input

Copy
[`01-PROJECT-INPUT-TEMPLATE.md`](01-PROJECT-INPUT-TEMPLATE.md) to
`input/PROJECT_INPUT.md`.

Replace every placeholder with the new course information. Decide:

- Project name and description.
- Source and study languages.
- Brand initials and restrained colors.
- Content mode: source-only, source plus generated, or generated-only.
- Allowed question types and question counts.
- Practice and Mock Exam defaults.
- Human-review policy for generated questions.
- GitHub repository, branch, and public URL.
- What to do when an official answer key is missing.

Do not leave a project decision blank.

## Step 4: Create the configuration

Copy
[`examples/project-config.example.json`](examples/project-config.example.json)
to `input/project-config.json`.

Change the example values to match `input/PROJECT_INPUT.md`. Keep the same JSON
structure and value types. If the content mode is source-only, set both
generated-question quotas to zero.

Check that the JSON parses:

```powershell
python -m json.tool input/project-config.json
```

## Step 5: Validate the factory kit

Run these commands from the project root:

```powershell
python -B scripts/validate_factory_kit.py
python -B -m unittest scripts.test_validate_factory_kit -v
```

Continue only when the validator prints:

```text
Validated study-site factory kit.
```

## Step 6: Start the Codex build

Open a new Codex task at the project root and send this message:

```text
Use docs/study-site-factory/10-MASTER-BUILD-PROMPT.md.

Project input: input/PROJECT_INPUT.md
Configuration: input/project-config.json
Materials: input/materials/

Build the complete source-backed study website. Follow every blocking gate,
keep official and generated content separate, and stop rather than guessing
when evidence is missing.
```

The master prompt tells Codex which factory document to read at each stage. You
do not need to paste the full PRD or repeat the product idea in chat.

## Step 7: Review the generated work

Codex should produce and validate:

- A source inventory and source-audit report.
- Modules, learning objectives, and Material lessons.
- Official questions preserved from the supplied files.
- Generated MCQ and True/False practice questions when enabled.
- Translations, explanations, short notes, and revision summaries.
- Review lists for missing, conflicting, or weak evidence.
- A simple static website using HTML, CSS, vanilla JavaScript, JSON, and
  LocalStorage.
- Content-quality, question-quality, browser, and final QA reports.

Check every review item. Never convert an uncertain answer into an official
answer by guessing. High-stakes generated questions require human approval.

## Step 8: Test the website

Run every command recorded in the project's final QA report. At minimum, check:

- The project-specific Python and JavaScript tests.
- JSON parsing and deterministic builder check modes.
- Desktop and mobile layouts.
- Light and dark themes.
- LTR and RTL content.
- Material reading and linked Practice.
- Practice feedback and explanations.
- Mock Exam answer secrecy before submission.
- Results, search, filters, bookmarks, and progress import/export.
- Zero relevant browser-console errors.

Fix every blocking failure before handoff.

## Step 9: Approve and deploy

Deployment is a separate decision. A configured repository or public URL does
not authorize publishing.

After the content and QA reports pass:

1. Review the final counts and unresolved items.
2. Give explicit deployment approval.
3. Follow
   [`11-HANDOFF-AND-DEPLOYMENT.md`](11-HANDOFF-AND-DEPLOYMENT.md).
4. Verify the deployed commit, HTML, every public JSON payload, stable IDs, and
   browser smoke-test evidence.

## Common mistakes

- Do not rename or delete source files after extraction without restarting the
  affected workflow stage.
- Do not mix official questions and generated questions in an unlabeled pool.
- Do not describe generated explanations or questions as official content.
- Do not make review-only questions scoreable.
- Do not manually edit deterministic output files without updating their source
  records and rebuilding them.
- Do not deploy because a repository is configured; require explicit approval.
- Do not rerun completed stages when their input hashes are unchanged.

## Final checklist

- [ ] All materials are inside `input/materials/`.
- [ ] `input/PROJECT_INPUT.md` is complete.
- [ ] `input/project-config.json` parses and matches the project input.
- [ ] The factory validator and tests pass.
- [ ] The master build prompt was used from the project root.
- [ ] Every source location was inventoried and reviewed.
- [ ] Official, generated, and review-only content is clearly separated.
- [ ] Material lessons, explanations, revision content, MCQ, and True/False
      questions meet their quality rules.
- [ ] Automated and browser QA gates pass.
- [ ] Human review is complete where required.
- [ ] Deployment has explicit approval and public verification evidence.

For the shortest version of this workflow, use
[`00-QUICK-START.md`](00-QUICK-START.md). For the exact agent instructions, use
[`10-MASTER-BUILD-PROMPT.md`](10-MASTER-BUILD-PROMPT.md).
