# Operating Systems Study Site Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Build and verify a complete bilingual Operating Systems study website from every PDF in `D:\UNI - EELU\0\PREVIOUS CONTENT\S-5\OS\Lectures`.

**Architecture:** A deterministic Python ingestion and build pipeline converts 21 PDF lecture decks into traceable source-page records, seven course modules, 21 bilingual lessons, 210 generated exam questions, and separate Arabic question guidance. In this isolated feature branch, the existing ITS static site is replaced with an Operating Systems edition that consumes the validated JSON and provides Material, Practice, Mock Exam, Revision, Mistakes, Bookmarks, search, filtering, progress, and theme flows through browser LocalStorage; the original ITS site remains unchanged on `master`.

**Tech Stack:** Python 3.12 with `pypdf` for extraction and validation; HTML5, CSS3, vanilla ES modules, JSON, browser LocalStorage; Node.js built-in test runner; browser verification through the Codex in-app browser or Playwright fallback; GitHub Pages static deployment.

**Spec:** `docs/superpowers/specs/2026-08-20-study-site-documentation-factory-design.md`

## Global Constraints

- Use all 21 PDFs and all 517 pages in natural lecture order; cover every substantive teaching page and explicitly classify cover, divider, reference, and closing pages as non-teaching pages.
- Do not copy the PDFs into the public website or Git history. Preserve provenance using source filename, one-based PDF page, section title, SHA-256 digest, page count, and source ID.
- The product uses plain HTML, CSS, vanilla JavaScript, JSON, and LocalStorage only. The final static folder has no runtime package dependency, build step, backend, database, or account system.
- Create seven modules for Chapters 1, 2, 3, 5, 6, 8, and 9 and exactly 21 lessons, one lesson per source PDF.
- Each lesson provides English source-oriented concepts plus clear Arabic study guidance, objectives, a revision summary, key terms, worked examples where supported, common mistakes, exam tips, recap points, and exact page references.
- Generate exactly 10 questions per lesson when the material supports them: six four-option MCQs and four True/False questions, for a target of 210 questions. If a lesson cannot support 10 unique claims, generate fewer and record the shortfall instead of inventing content.
- Each question is visibly labeled `Generated from course material`, uses an English exam-style prompt, has an Arabic translation, an evidence-based answer, two or three short Arabic explanation paragraphs, and a concise Arabic revision note.
- Per ten-question lesson use three easy, five medium, and two hard questions; target three remember, five apply, and two analyze questions. Balance True/False answers across the complete pool.
- Every lesson claim and question answer must be supported by one or more source references. Unsupported, ambiguous, or contradictory items use `review.status: "needs-review"`, remain unscored, and stay out of Mock Exams.
- Material content and generated questions remain separate data families. Generated guidance never silently becomes official source content.
- Keep the existing clean blue/cyan study-site visual system, responsive desktop sidebar and mobile navigation, readable Arabic RTL blocks, accessible focus states, and light/dark themes.
- Persist progress under `os-study-progress-v1`; validate imports and provide export/reset controls.
- Escape all source-derived text before rendering it as HTML.
- Publish only after validators, unit tests, browser flows, desktop/mobile visual checks, and public URL verification succeed.

---

### Task 1: Create the OS project configuration and complete source ingestion

**Files:**
- Create: `input/PROJECT_INPUT.md`
- Create: `input/project-config.json`
- Create: `scripts/extract_os_material.py`
- Create: `scripts/test_extract_os_material.py`
- Create: `content/source-manifest.json`
- Create: `extraction/os-pages.json`
- Create: `reports/SOURCE_AUDIT_REPORT.md`

**Interfaces:**
- Consumes: the 21 PDFs below `D:\UNI - EELU\0\PREVIOUS CONTENT\S-5\OS\Lectures`.
- Produces: `build_source_records(pdf_root: Path) -> list[dict]`, `extract_page_records(source: dict) -> list[dict]`, and deterministic JSON shaped as `{version, course, generatedAtPolicy, sources, pages}`.
- A source record contains `id`, `file`, `chapter`, `part`, `pages`, `sha256`, and `title`; a page record contains `sourceId`, `page`, `text`, `characterCount`, and `classification`.

- [ ] **Step 1: Write failing ingestion tests**

```python
def test_natural_source_order_and_complete_page_inventory():
    payload = build_payload(FIXTURE_ROOT)
    assert [source["file"] for source in payload["sources"]] == [
        "1-ch1_part1.pdf", "2-ch1_part2.pdf"
    ]
    assert len(payload["pages"]) == sum(source["pages"] for source in payload["sources"])


def test_page_numbers_are_one_based_and_text_is_preserved():
    payload = build_payload(FIXTURE_ROOT)
    assert min(page["page"] for page in payload["pages"]) == 1
    assert all(page["characterCount"] == len(page["text"]) for page in payload["pages"])
```

- [ ] **Step 2: Run the tests and verify they fail**

Run: `python -m unittest scripts.test_extract_os_material -v`

Expected: FAIL because `scripts.extract_os_material` does not exist.

- [ ] **Step 3: Implement deterministic extraction and configuration**

Implement natural numeric filename ordering, SHA-256 streaming, `pypdf.PdfReader` page extraction, Unicode normalization, one-based pages, and page classifications limited to `teaching`, `cover`, `divider`, `reference`, or `closing`. Store the original absolute source folder only in `input/PROJECT_INPUT.md`; public payloads store filenames, IDs, and page references without machine-specific paths.

- [ ] **Step 4: Generate and validate the complete artifacts**

Run:

```powershell
python scripts/extract_os_material.py --pdf-root "D:\UNI - EELU\0\PREVIOUS CONTENT\S-5\OS\Lectures"
python -m unittest scripts.test_extract_os_material -v
```

Expected: 21 source records, 517 page records, non-empty extracted text on teaching pages, stable hashes, and an audit report containing exact counts per file and page class.

- [ ] **Step 5: Commit**

```powershell
git add input scripts/extract_os_material.py scripts/test_extract_os_material.py content/source-manifest.json extraction/os-pages.json reports/SOURCE_AUDIT_REPORT.md
git commit -m "data: ingest operating systems lecture PDFs"
```

---

### Task 2: Author lessons and questions for Chapters 1 and 2

**Files:**
- Create: `content/os/ch01-ch02.json`
- Create: `scripts/test_os_content_parts.py`

**Interfaces:**
- Consumes: `extraction/os-pages.json` for source IDs `os-lec-01` through `os-lec-07`.
- Produces: `{modules, lessons, questions, explanations}` containing two modules, seven lessons, up to 70 questions, and one explanation per question.
- Each lesson declares `coveredPages` as inclusive page ranges and `nonTeachingPages` so every page in its PDF is accounted for exactly once.

- [ ] **Step 1: Write failing content-contract tests**

```python
def test_chapters_one_and_two_have_seven_traceable_lessons():
    part = load_part("content/os/ch01-ch02.json")
    assert [module["chapter"] for module in part["modules"]] == [1, 2]
    assert len(part["lessons"]) == 7
    assert_all_source_pages_accounted_for(part, source_ids={f"os-lec-{n:02d}" for n in range(1, 8)})


def test_every_generated_question_has_separate_arabic_guidance():
    part = load_part("content/os/ch01-ch02.json")
    explanations = {item["questionId"]: item for item in part["explanations"]}
    for question in part["questions"]:
        assert question["origin"] == "generated"
        assert question["id"] in explanations
        assert 2 <= len(explanations[question["id"]]["paragraphsAr"]) <= 3
```

- [ ] **Step 2: Run the tests and verify they fail**

Run: `python -m unittest scripts.test_os_content_parts -v`

Expected: FAIL because the content part does not exist.

- [ ] **Step 3: Author the seven lessons from the extracted source pages**

Create one lesson for each of `1-ch1_part1.pdf` through `7-ch2_part3.pdf`. Preserve the chapter flow, convert every substantive slide into a named lesson section, and provide complete bilingual study guidance without importing facts that are not supported by the cited pages.

- [ ] **Step 4: Author and self-check the generated question pool**

For each lesson, write six MCQs and four True/False questions when supported. MCQs have exactly four plausible options and one defensible answer. Every question carries `difficulty`, `bloomLevel`, `lessonId`, `sourceRefs`, `rationaleEn`, and `review`; every explanation carries `translationAr`, two or three short `paragraphsAr`, and `noteAr`.

- [ ] **Step 5: Run the focused content tests**

Run: `python -m unittest scripts.test_os_content_parts -v`

Expected: PASS for schema, page accounting, evidence references, unique IDs/prompts, type quotas, difficulty and Bloom distributions, True/False balance, and Arabic guidance length.

- [ ] **Step 6: Commit**

```powershell
git add content/os/ch01-ch02.json scripts/test_os_content_parts.py
git commit -m "content: add operating systems chapters one and two"
```

---

### Task 3: Author lessons and questions for Chapters 3 and 5

**Files:**
- Create: `content/os/ch03-ch05.json`
- Modify: `scripts/test_os_content_parts.py`

**Interfaces:**
- Consumes: `extraction/os-pages.json` for source IDs `os-lec-08` through `os-lec-14` and the shared content contract introduced in Task 2.
- Produces: two modules, seven lessons, up to 70 questions, and one explanation per question without changing prior content IDs.

- [ ] **Step 1: Extend tests for the second content part**

```python
def test_chapters_three_and_five_have_seven_traceable_lessons():
    part = load_part("content/os/ch03-ch05.json")
    assert [module["chapter"] for module in part["modules"]] == [3, 5]
    assert len(part["lessons"]) == 7
    assert_all_source_pages_accounted_for(part, source_ids={f"os-lec-{n:02d}" for n in range(8, 15)})
```

- [ ] **Step 2: Run the focused test and verify it fails**

Run: `python -m unittest scripts.test_os_content_parts.OSContentPartTests.test_chapters_three_and_five_have_seven_traceable_lessons -v`

Expected: FAIL because `content/os/ch03-ch05.json` does not exist.

- [ ] **Step 3: Author the seven lessons from Lectures 8-14**

Cover process concepts, scheduling, synchronization foundations, and every Chapter 3 and Chapter 5 topic present in the extracted pages. Keep algorithms, tables, examples, and diagrams accurate to their cited slides; explain them in clear Arabic study prose.

- [ ] **Step 4: Author the second generated question pool**

Apply the same ten-question target, per-lesson distribution, evidence, Arabic translation, two-to-three-paragraph explanation, and revision-note contract from Task 2.

- [ ] **Step 5: Run all content-part tests**

Run: `python -m unittest scripts.test_os_content_parts -v`

Expected: PASS for both content files with no duplicate lesson, question, or explanation IDs across parts.

- [ ] **Step 6: Commit**

```powershell
git add content/os/ch03-ch05.json scripts/test_os_content_parts.py
git commit -m "content: add operating systems chapters three and five"
```

---

### Task 4: Author lessons and questions for Chapters 6, 8, and 9

**Files:**
- Create: `content/os/ch06-ch08-ch09.json`
- Modify: `scripts/test_os_content_parts.py`

**Interfaces:**
- Consumes: `extraction/os-pages.json` for source IDs `os-lec-15` through `os-lec-21` and the shared content contract.
- Produces: three modules, seven lessons, up to 70 questions, and one explanation per question.

- [ ] **Step 1: Extend tests for the final content part**

```python
def test_chapters_six_eight_and_nine_have_seven_traceable_lessons():
    part = load_part("content/os/ch06-ch08-ch09.json")
    assert [module["chapter"] for module in part["modules"]] == [6, 8, 9]
    assert len(part["lessons"]) == 7
    assert_all_source_pages_accounted_for(part, source_ids={f"os-lec-{n:02d}" for n in range(15, 22)})
```

- [ ] **Step 2: Run the focused test and verify it fails**

Run: `python -m unittest scripts.test_os_content_parts.OSContentPartTests.test_chapters_six_eight_and_nine_have_seven_traceable_lessons -v`

Expected: FAIL because `content/os/ch06-ch08-ch09.json` does not exist.

- [ ] **Step 3: Author the seven lessons from Lectures 15-21**

Cover synchronization tools, deadlocks, memory management, and virtual memory exactly as presented in Chapters 6, 8, and 9. Preserve formulas, algorithm steps, resource-allocation examples, allocation strategies, paging concepts, and cited slide boundaries.

- [ ] **Step 4: Author the final generated question pool**

Apply the same ten-question target, per-lesson distribution, evidence, Arabic translation, explanation, and note contract. Across the combined 21-lesson pool, ensure True and False answers differ by no more than one.

- [ ] **Step 5: Run all content-part tests**

Run: `python -m unittest scripts.test_os_content_parts -v`

Expected: PASS for all three content files and all cross-part uniqueness and balance checks.

- [ ] **Step 6: Commit**

```powershell
git add content/os/ch06-ch08-ch09.json scripts/test_os_content_parts.py
git commit -m "content: add operating systems chapters six eight and nine"
```

---

### Task 5: Build deterministic website payloads and coverage reports

**Files:**
- Create: `scripts/build_os_site_data.py`
- Create: `scripts/validate_os_site.py`
- Create: `scripts/test_build_os_site_data.py`
- Create: `study-website/data/course.json`
- Create: `study-website/data/lessons.json`
- Create: `study-website/data/questions.json`
- Create: `study-website/data/explanations-ar.json`
- Create: `reports/CONTENT_COVERAGE_REPORT.md`
- Create: `reports/QUESTION_QUALITY_REPORT.md`

**Interfaces:**
- Consumes: the three `content/os/*.json` parts plus `content/source-manifest.json` and `extraction/os-pages.json`.
- Produces: `build_payloads(parts: list[dict]) -> dict[str, dict]`, `validate_payloads(payloads: dict[str, dict]) -> list[str]`, four deterministic public JSON payloads, and measured reports.

- [ ] **Step 1: Write failing builder tests**

```python
def test_build_combines_all_modules_lessons_questions_and_explanations():
    payloads = build_payloads(load_content_parts())
    assert len(payloads["course"]["modules"]) == 7
    assert len(payloads["lessons"]["lessons"]) == 21
    assert len(payloads["questions"]["questions"]) == 210
    assert len(payloads["explanations-ar"]["explanations"]) == 210


def test_every_public_reference_resolves_to_a_real_source_page():
    errors = validate_payloads(build_payloads(load_content_parts()))
    assert errors == []
```

- [ ] **Step 2: Run the tests and verify they fail**

Run: `python -m unittest scripts.test_build_os_site_data -v`

Expected: FAIL because the builder does not exist.

- [ ] **Step 3: Implement deterministic assembly and strict validation**

Sort modules, lessons, questions, explanations, and references by stable IDs. Validate allowed keys, referential integrity, page bounds, exact answer types, four-option MCQs, non-empty rationales, distribution counts, review gating, Arabic guidance, HTML-dangerous source text handling, and complete page accounting. A `--check` mode rebuilds in memory and fails on drift without writing files.

- [ ] **Step 4: Generate public payloads and measured reports**

Run:

```powershell
python scripts/build_os_site_data.py
python scripts/validate_os_site.py
python -m unittest scripts.test_build_os_site_data -v
```

Expected: all commands exit 0; reports state exact source, page, lesson, question, type, difficulty, Bloom, review, and source-coverage totals.

- [ ] **Step 5: Commit**

```powershell
git add scripts/build_os_site_data.py scripts/validate_os_site.py scripts/test_build_os_site_data.py study-website/data reports/CONTENT_COVERAGE_REPORT.md reports/QUESTION_QUALITY_REPORT.md
git commit -m "build: create validated operating systems payloads"
```

---

### Task 6: Implement tested study-domain modules

**Files:**
- Create: `study-website/js/data.js`
- Modify: `study-website/js/storage.js`
- Modify: `study-website/js/questions.js`
- Modify: `study-website/js/quiz.js`
- Create: `study-website/js/exam.js`
- Modify: `study-website/js/revision.js`
- Create: `study-website/tests/data.test.mjs`
- Create: `study-website/tests/storage.test.mjs`
- Create: `study-website/tests/quiz-exam.test.mjs`
- Modify: `study-website/tests/revision.test.mjs`
- Delete: `study-website/js/explanations.js`
- Delete: `study-website/js/explanations-view.js`
- Delete: `study-website/js/question-renderer.js`
- Delete: `study-website/js/statistics.js`
- Delete: `study-website/tests/data-validation.test.mjs`
- Delete: `study-website/tests/explanations-data.test.mjs`
- Delete: `study-website/tests/explanations-view.test.mjs`
- Delete: `study-website/tests/explanations.test.mjs`
- Delete: `study-website/tests/question-renderer.test.mjs`
- Delete: `study-website/tests/questions.test.mjs`
- Delete: `study-website/tests/quiz.test.mjs`
- Delete: `study-website/tests/source-coverage.test.mjs`
- Delete: `study-website/tests/storage-statistics.test.mjs`
- Delete: `study-website/tests/fixtures/q103-selection-cases.json`

**Interfaces:**
- Produces: `loadCourseData()`, `filterLessons()`, `filterQuestions()`, `scoreResponse()`, `createPracticeSession()`, `answerPracticeQuestion()`, `createExam()`, `submitExam()`, `createDefaultState()`, `loadState()`, `saveState()`, `recordAttempt()`, `toggleBookmark()`, `markLessonComplete()`, `getRevisionSummary()`, `getMistakeQuestions()`, and `getBookmarkedQuestions()`.

- [ ] **Step 1: Write failing domain tests**

```javascript
test("practice reveals Arabic guidance only after an answer", () => {
  const session = createPracticeSession([mcq], { count: 1, order: "original" });
  assert.equal(session.feedbackVisible, false);
  const answered = answerPracticeQuestion(session, mcq.correctAnswer);
  assert.equal(answered.feedbackVisible, true);
});

test("mock exams exclude review items and hide correctness until submit", () => {
  const exam = createExam([validatedQuestion, reviewQuestion], { count: 10 }, 1000);
  assert.deepEqual(exam.questionIds, [validatedQuestion.id]);
  const answered = answerExamQuestion(exam, validatedQuestion.correctAnswer);
  assert.equal(answered.answers[validatedQuestion.id].correct, undefined);
});
```

- [ ] **Step 2: Run the new tests and verify they fail**

Run: `node --test study-website/tests/data.test.mjs study-website/tests/storage.test.mjs study-website/tests/quiz-exam.test.mjs study-website/tests/revision.test.mjs`

Expected: FAIL because the ES modules do not exist.

- [ ] **Step 3: Implement immutable data, scoring, session, and storage logic**

Use storage key `os-study-progress-v1`, schema version `1`, exact question IDs, safe copies, absolute exam end times, no mutation of canonical data, validated import/export, and deterministic test injection for random ordering. MCQ answers are zero-based option indexes; True/False answers are Booleans.

- [ ] **Step 4: Implement revision and collection logic**

Calculate lesson completion, overall accuracy, weak modules/topics, missed-question ranking, bookmarks, recent sessions, and revision cards. Keep Arabic guidance out of active Mock Exams and expose it only in Practice feedback and submitted reviews.

- [ ] **Step 5: Remove the obsolete ITS-only modules and tests**

Delete only the explicitly listed tracked files after verifying that no new OS module imports them. Leave the original ITS history recoverable on `master` and remove no files outside this isolated worktree.

- [ ] **Step 6: Run all domain tests**

Run: `node --test study-website/tests/*.test.mjs`

Expected: PASS for loading, filtering, scoring, review gating, persistence, import/export, Practice, Mock Exam, revision, mistakes, bookmarks, and lesson progress.

- [ ] **Step 7: Commit**

```powershell
git add study-website/js study-website/tests
git commit -m "feat: add operating systems study domain logic"
```

---

### Task 7: Build the responsive bilingual study interface

**Files:**
- Modify: `study-website/index.html`
- Modify: `study-website/css/styles.css`
- Modify: `study-website/js/app.js`
- Modify: `study-website/README.md`
- Create: `study-website/tests/app.test.mjs`
- Modify: `START_WEBSITE.bat`
- Delete: `study-website/assets/source-pages/bank-page-16.jpg`
- Delete: `study-website/assets/source-pages/bank-page-19.jpg`
- Delete: `study-website/assets/source-pages/bank-page-42.jpg`
- Delete: `study-website/assets/source-pages/bank-page-44.jpg`
- Delete: `study-website/assets/source-pages/bank-page-5.jpg`
- Delete: `study-website/assets/source-pages/bank-page-58.jpg`
- Delete: `study-website/assets/source-pages/bank-page-83.jpg`
- Delete: `study-website/assets/source-pages/bank-page-84.jpg`
- Delete: `study-website/assets/source-pages/bank-page-95.jpg`
- Delete: `study-website/assets/source-pages/pretest-page-46.jpg`
- Delete: `study-website/QUESTION_EXTRACTION_REPORT.md`

**Interfaces:**
- Consumes: public JSON payloads and Task 6 domain modules.
- Produces: hash routes `dashboard`, `material`, `lesson/:id`, `questions`, `explanations`, `practice`, `exam`, `revision`, `mistakes`, `bookmarks`, and `settings`; `routeFromHash(hash)`, `escapeHtml(value)`, and `shouldHandleShortcut(event)`.

- [ ] **Step 1: Write failing routing and rendering-safety tests**

```javascript
test("lesson hashes preserve stable lesson IDs", () => {
  assert.deepEqual(routeFromHash("#/lesson/os-ch01-part1"), {
    name: "lesson",
    id: "os-ch01-part1"
  });
});

test("source-derived markup is escaped", () => {
  assert.equal(escapeHtml('<img src=x onerror="alert(1)">'), "&lt;img src=x onerror=&quot;alert(1)&quot;&gt;");
});
```

- [ ] **Step 2: Run the focused tests and verify they fail**

Run: `node --test study-website/tests/app.test.mjs`

Expected: FAIL because the application shell does not exist.

- [ ] **Step 3: Implement the application shell and visual system**

Reuse the clean blue/cyan ITS visual direction with a desktop sidebar above 900px and mobile bottom navigation below 900px. Use semantic HTML, true white light surfaces, a dark theme, accessible cyan/blue accents, readable content widths, Arabic `dir="rtl"` guidance blocks, visible generated-content labels, focus rings, and reduced-motion support.

- [ ] **Step 4: Implement all primary routes and interactions**

Dashboard shows course coverage, progress, accuracy, weak modules, and resume actions. Material supports search, module filtering, completion filtering, lesson navigation, and linked practice. Lessons show objectives, revision summary, bilingual explanation, sections, terms, examples, mistakes, tips, recap, references, completion, and linked questions. Implement full Practice, Mock Exam, Question Bank, Question Explanations, Revision, Mistakes, Bookmarks, theme, import, export, reset, empty states, dialogs, and keyboard shortcuts.

- [ ] **Step 5: Remove the old ITS-only source images and report**

Delete only the explicitly listed tracked assets and `QUESTION_EXTRACTION_REPORT.md` after confirming the new app has no references to them. The OS website publishes generated guidance and page citations, not the original PDFs or old ITS source-page images.

- [ ] **Step 6: Run unit tests and local smoke checks**

Run:

```powershell
node --check study-website/js/app.js
node --test study-website/tests/*.test.mjs
python -m http.server 8000 --directory study-website
```

Expected: syntax and unit tests pass; all routes load without console errors; long English and Arabic text remains readable at desktop and mobile widths.

- [ ] **Step 7: Commit**

```powershell
git add study-website START_WEBSITE.bat
git commit -m "feat: build bilingual operating systems study interface"
```

---

### Task 8: Complete automated QA, visual verification, and deployment setup

**Files:**
- Create: `study-website/tests/browser-check.mjs`
- Create: `reports/FINAL_QA_REPORT.md`
- Modify: `.github/workflows/pages.yml`
- Modify: `study-website/README.md`

**Interfaces:**
- Consumes: the complete static site and all validators/tests.
- Produces: reproducible browser-flow evidence, desktop/mobile screenshots in temporary QA storage, a final QA report, and a GitHub Pages workflow that publishes only `study-website`.

- [ ] **Step 1: Write the browser smoke test**

The script records `pageerror` and console errors, loads all routes, searches Material, opens and completes a lesson, answers MCQ and True/False questions, checks Arabic explanations, bookmarks and revisits a question, finishes Practice, submits a Mock Exam, opens Revision and Mistakes, toggles dark mode, exports progress, reloads to confirm persistence, imports the export, and repeats the primary navigation at 390x844.

```javascript
const errors = [];
page.on("pageerror", error => errors.push(error.message));
page.on("console", message => {
  if (message.type() === "error") errors.push(message.text());
});
assert.deepEqual(errors, []);
```

- [ ] **Step 2: Run the complete local verification suite**

Run:

```powershell
python scripts/extract_os_material.py --check --pdf-root "D:\UNI - EELU\0\PREVIOUS CONTENT\S-5\OS\Lectures"
python scripts/build_os_site_data.py --check
python scripts/validate_os_site.py
python -m unittest discover -s scripts -p "test_*.py"
node --check study-website/js/app.js
node --test study-website/tests/*.test.mjs
node study-website/tests/browser-check.mjs
```

Expected: every command exits 0 and the browser check reports zero page or console errors.

- [ ] **Step 3: Perform visual and responsive inspection**

Capture dashboard, Material index, a long lesson, Practice feedback with Arabic guidance, Mock Exam, Revision, light mode, dark mode, 1440px desktop, and 390x844 mobile. Inspect screenshots with `view_image`; fix clipping, overflow, weak contrast, broken RTL layout, accidental wrapping, unreadable typography, or inactive controls.

- [ ] **Step 4: Finalize documentation and deployment evidence**

Document the 21-PDF/517-page source coverage, exact lesson and question totals, generated-content policy, local server command, data structure, correction workflow, test commands, LocalStorage key, export/import, limitations, and GitHub Pages workflow. `FINAL_QA_REPORT.md` records commands, counts, browser paths, viewport sizes, screenshot names, and deployment verification fields.

- [ ] **Step 5: Re-run verification and commit**

```powershell
git add .github/workflows/pages.yml study-website reports/FINAL_QA_REPORT.md
git commit -m "test: verify and prepare operating systems study site"
```

Expected: the branch is clean after the commit and all local validation remains green.
