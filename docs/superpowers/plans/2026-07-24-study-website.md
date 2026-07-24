# ITS Study Website Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Build a complete static study website from every official question and answer in the two supplied PDFs.

**Architecture:** A Python extraction and validation pipeline produces one canonical `questions.json` with merged duplicates and complete source references. A dependency-free browser application loads that JSON and splits routing, storage, statistics, rendering, practice, exam, revision, and question-bank behavior into focused ES modules.

**Tech Stack:** Python 3 with pypdf/pdfplumber for extraction helpers, HTML5, CSS3, vanilla JavaScript ES modules, JSON, LocalStorage, Node.js built-in test runner, and Playwright only for external browser verification.

## Global Constraints

- Include every question from `Device_Configuration_and_Management_Eng_Ali_Mohamed.pdf` and `ITS OD 103 Pre-Test.pdf`.
- Never add outside questions, answers, explanations, or factual content.
- Preserve original wording except for obvious OCR and formatting corrections.
- Never guess unclear text or answers; set `needsReview: true`.
- Use only HTML, CSS, vanilla JavaScript, JSON, and LocalStorage in the delivered website.
- Do not add a frontend framework, backend, database, authentication, package installation, or build step.
- Keep exact source PDF names, original question numbers, and PDF page numbers.
- Merge duplicates but retain every source reference.
- Exclude unresolved questions from scored exams by default.

---

## File Map

- `scripts/extract_questions.py`: extracts page text, renders OCR-only pages, and writes raw candidates.
- `scripts/validate_questions.py`: validates schema, answers, source coverage, duplicates, and report totals.
- `extraction/raw-questions.json`: auditable source-by-source extraction before merging.
- `study-website/data/questions.json`: canonical validated question collection.
- `study-website/index.html`: semantic application shell and view containers.
- `study-website/css/styles.css`: responsive design system and all view styles.
- `study-website/js/questions.js`: data loading, normalization, filtering, and safe choice shuffling.
- `study-website/js/storage.js`: versioned LocalStorage state, import/export, and reset.
- `study-website/js/statistics.js`: dashboard, session, exam, and weak-topic calculations.
- `study-website/js/question-renderer.js`: safe rendering and answer collection for every question type.
- `study-website/js/quiz.js`: practice session state machine.
- `study-website/js/exam.js`: exam state machine, timer, submission, and review.
- `study-website/js/revision.js`: revision cards, mistakes, and bookmark collections.
- `study-website/js/app.js`: routing, event wiring, dashboard, bank, settings, and startup.
- `study-website/tests/*.test.mjs`: pure logic and data tests using Node's built-in test runner.
- `study-website/tests/browser-check.mjs`: browser smoke and interaction checks.
- `study-website/QUESTION_EXTRACTION_REPORT.md`: extraction audit and manual-review list.
- `study-website/README.md`: running, editing, validation, deployment, and limitations.

---

### Task 1: Build the PDF extraction audit

**Files:**
- Create: `scripts/extract_questions.py`
- Create: `extraction/raw-questions.json`
- Create: `study-website/tests/source-coverage.test.mjs`

**Interfaces:**
- Consumes: the two PDFs at the workspace root.
- Produces: `raw-questions.json` entries shaped as `{sourceId, sourceFile, sourcePage, sourceQuestion, rawText, answerMarks, sourceImage, extractionMethod, needsReview, reviewNotes}`.

- [ ] **Step 1: Write the failing source-coverage test**

```js
import test from "node:test";
import assert from "node:assert/strict";
import { readFile } from "node:fs/promises";

test("raw extraction covers both official collections", async () => {
  const raw = JSON.parse(await readFile("../extraction/raw-questions.json", "utf8"));
  assert.equal(raw.filter((q) => q.sourceId === "bank-105").length, 105);
  assert.equal(raw.filter((q) => q.sourceId === "pretest-70").length, 70);
  assert.ok(raw.every((q) => q.sourcePage > 0 && q.sourceQuestion > 0));
});
```

- [ ] **Step 2: Run the test and verify it fails**

Run from `study-website/`:

```powershell
node --test tests/source-coverage.test.mjs
```

Expected: FAIL because `extraction/raw-questions.json` does not exist.

- [ ] **Step 3: Implement extraction**

Implement these concrete functions in `scripts/extract_questions.py`:

```python
def extract_bank(pdf_path: Path) -> list[dict]:
    """Return exactly 105 entries from PDF pages 2-106."""

def extract_pretest(pdf_path: Path, image_dir: Path) -> list[dict]:
    """Return exactly 70 entries from PDF pages 7-76 using OCR/rendered evidence."""

def normalize_text(value: str) -> str:
    return " ".join(value.replace("\x00", " ").split())

def write_raw(entries: list[dict], output_path: Path) -> None:
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(
        json.dumps(entries, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )
```

For every page, retain the rendered page image path when text or answer markings are graphical. Record an explicit review note if OCR confidence or answer marking is unclear.

- [ ] **Step 4: Manually compare rendered evidence**

Render all 175 question pages under `tmp/pdfs/`, compare each extracted prompt, option, and official answer to the visible page, and correct only obvious OCR or layout errors in `raw-questions.json`.

- [ ] **Step 5: Run the source-coverage test**

Run:

```powershell
node --test tests/source-coverage.test.mjs
```

Expected: PASS with 105 bank entries and 70 pre-test entries.

- [ ] **Step 6: Commit**

```powershell
git add scripts/extract_questions.py extraction/raw-questions.json study-website/tests/source-coverage.test.mjs
git commit -m "data: extract both official question collections"
```

---

### Task 2: Create and validate the canonical question bank

**Files:**
- Create: `scripts/validate_questions.py`
- Create: `study-website/data/questions.json`
- Create: `study-website/tests/data-validation.test.mjs`
- Create: `study-website/QUESTION_EXTRACTION_REPORT.md`

**Interfaces:**
- Consumes: `extraction/raw-questions.json`.
- Produces: `{version, course, generatedFrom, questions}` where each question contains `id`, `type`, `prompt`, type-specific answer data, `sources`, `explanation`, `needsReview`, and `reviewNotes`.

- [ ] **Step 1: Write failing schema and answer-mapping tests**

```js
import test from "node:test";
import assert from "node:assert/strict";
import { readFile } from "node:fs/promises";

const data = JSON.parse(await readFile(new URL("../data/questions.json", import.meta.url)));

test("canonical bank has stable unique IDs and complete sources", () => {
  const ids = data.questions.map((q) => q.id);
  assert.equal(new Set(ids).size, ids.length);
  assert.ok(data.questions.every((q) => q.prompt && q.sources.length >= 1));
  assert.equal(
    data.questions.flatMap((q) => q.sources).filter((s) => s.collection === "bank-105").length,
    105
  );
  assert.equal(
    data.questions.flatMap((q) => q.sources).filter((s) => s.collection === "pretest-70").length,
    70
  );
});

test("every scored question has a valid official answer", () => {
  for (const q of data.questions.filter((item) => !item.needsReview)) {
    assert.notEqual(q.correctAnswer, null, q.id);
    if (q.type === "mcq") {
      assert.ok(Number.isInteger(q.correctAnswer));
      assert.ok(q.correctAnswer >= 0 && q.correctAnswer < q.options.length);
    }
  }
});
```

- [ ] **Step 2: Run tests and verify failure**

Run:

```powershell
node --test tests/data-validation.test.mjs
```

Expected: FAIL because the canonical data file does not exist.

- [ ] **Step 3: Implement normalization, classification, and duplicate merging**

Implement:

```python
SUPPORTED_TYPES = {
    "mcq", "multi-select", "true-false", "true-false-group",
    "matching", "ordering"
}

def duplicate_key(prompt: str) -> str:
    value = re.sub(r"[^a-z0-9 ]+", " ", prompt.lower())
    return " ".join(value.split())

def merge_duplicates(entries: list[dict]) -> list[dict]:
    """Merge equivalent prompts and append all distinct source references."""

def validate_question(question: dict) -> list[str]:
    """Return concrete schema or answer-mapping errors for one question."""
```

Do not merge near-duplicates automatically when choices or official answers differ. Mark such pairs for review.

- [ ] **Step 4: Generate the extraction report**

Write exact counts for both PDF page totals, 175 raw entries, canonical unique questions, each question type, merged duplicates, unclear items, OCR-only pages, source-page failures, and every formatting correction.

- [ ] **Step 5: Run validation**

Run:

```powershell
python scripts/validate_questions.py
node --test tests/data-validation.test.mjs
```

Expected: validator exits 0; tests PASS; all unresolved items are listed in the report.

- [ ] **Step 6: Commit**

```powershell
git add scripts/validate_questions.py study-website/data/questions.json study-website/tests/data-validation.test.mjs study-website/QUESTION_EXTRACTION_REPORT.md
git commit -m "data: validate and merge official questions"
```

---

### Task 3: Build the static application shell and design system

**Files:**
- Create: `study-website/index.html`
- Create: `study-website/css/styles.css`
- Create: `study-website/js/app.js`
- Create: `study-website/js/questions.js`
- Create: `study-website/tests/questions.test.mjs`

**Interfaces:**
- Consumes: `data/questions.json`.
- Produces: `loadQuestionBank(): Promise<QuestionBank>`, `filterQuestions(questions, filters): Question[]`, and hash routes for all main views.

- [ ] **Step 1: Write a failing data-loader test**

```js
import test from "node:test";
import assert from "node:assert/strict";
import { filterQuestions } from "../js/questions.js";

test("filters by source, type, and status together", () => {
  const questions = [
    { id: "q1", type: "mcq", sources: [{ collection: "bank-105" }] },
    { id: "q2", type: "true-false", sources: [{ collection: "pretest-70" }] }
  ];
  const result = filterQuestions(questions, {
    source: "bank-105",
    type: "mcq",
    status: "unanswered",
    progress: {}
  });
  assert.deepEqual(result.map((q) => q.id), ["q1"]);
});
```

- [ ] **Step 2: Run the test and verify failure**

Run:

```powershell
node --test tests/questions.test.mjs
```

Expected: FAIL because `questions.js` has not been implemented.

- [ ] **Step 3: Implement question loading and filtering**

Export:

```js
export async function loadQuestionBank(url = "./data/questions.json") {}
export function filterQuestions(questions, filters) {}
export function shuffleQuestions(questions, random = Math.random) {}
export function shuffleChoices(question, random = Math.random) {}
```

`shuffleChoices` must return a copied question with remapped `correctAnswer`; it must never mutate canonical data.

- [ ] **Step 4: Build semantic view containers**

`index.html` must contain `#app-shell`, `#sidebar`, `#mobile-nav`, `#main-content`, `#toast-region`, `#dialog-root`, theme metadata, and module loading through:

```html
<script type="module" src="./js/app.js"></script>
```

- [ ] **Step 5: Implement the responsive visual foundation**

Define CSS custom properties for light/dark surfaces, text, muted text, primary cyan/blue, success, danger, warning, borders, shadows, spacing, radii, and readable content widths. Add desktop sidebar behavior above 900px and mobile bottom navigation below 900px.

- [ ] **Step 6: Run tests and manual shell check**

Run:

```powershell
node --test tests/questions.test.mjs
python -m http.server 8000 --directory study-website
```

Expected: tests PASS; `http://localhost:8000` loads without console errors.

- [ ] **Step 7: Commit**

```powershell
git add study-website/index.html study-website/css/styles.css study-website/js/app.js study-website/js/questions.js study-website/tests/questions.test.mjs
git commit -m "feat: add static study app shell"
```

---

### Task 4: Implement versioned progress storage and statistics

**Files:**
- Create: `study-website/js/storage.js`
- Create: `study-website/js/statistics.js`
- Create: `study-website/tests/storage-statistics.test.mjs`

**Interfaces:**
- Produces: `createDefaultState()`, `loadState(storage)`, `saveState(state, storage)`, `recordAttempt(state, attempt)`, `toggleBookmark(state, questionId)`, `exportState(state)`, `importState(json)`, `resetState(storage)`, `getDashboardStats(questions, state)`, and `getPerformanceBreakdown(questions, state, dimension)`.

- [ ] **Step 1: Write failing persistence and accuracy tests**

```js
test("recordAttempt keeps history and latest status", () => {
  const state = createDefaultState();
  const next = recordAttempt(state, {
    questionId: "q1", selectedAnswer: 2, correct: false, at: "2026-07-24T12:00:00Z"
  });
  assert.equal(next.progress.q1.incorrectAttempts, 1);
  assert.equal(next.progress.q1.status, "wrong");
  assert.equal(next.history.length, 1);
});

test("dashboard accuracy uses answered questions only", () => {
  const stats = getDashboardStats(
    [{ id: "q1" }, { id: "q2" }, { id: "q3" }],
    { progress: { q1: { status: "correct" }, q2: { status: "wrong" } } }
  );
  assert.equal(stats.accuracy, 50);
  assert.equal(stats.completion, 67);
});
```

- [ ] **Step 2: Run tests and verify failure**

Run:

```powershell
node --test tests/storage-statistics.test.mjs
```

Expected: FAIL because exports do not exist.

- [ ] **Step 3: Implement immutable state operations**

Use storage key `its-study-progress-v1` and schema version `1`. Validate imports by checking the version, plain-object fields, arrays, and string question IDs before returning imported state.

- [ ] **Step 4: Run tests**

Run:

```powershell
node --test tests/storage-statistics.test.mjs
```

Expected: PASS for save/load, corrupt JSON fallback, history, bookmarks, import rejection, accuracy, completion, and breakdowns.

- [ ] **Step 5: Commit**

```powershell
git add study-website/js/storage.js study-website/js/statistics.js study-website/tests/storage-statistics.test.mjs
git commit -m "feat: add progress storage and statistics"
```

---

### Task 5: Render and score every official question type

**Files:**
- Create: `study-website/js/question-renderer.js`
- Create: `study-website/tests/question-renderer.test.mjs`

**Interfaces:**
- Produces: `renderQuestion(question, context): string`, `normalizeResponse(question, formData): unknown`, `scoreResponse(question, response): {correct, earned, possible}`, and `renderAnswerReview(question, response): string`.

- [ ] **Step 1: Write failing scoring tests**

```js
test("scores grouped true-false with partial detail", () => {
  const q = {
    type: "true-false-group",
    statements: [{ correctAnswer: true }, { correctAnswer: false }, { correctAnswer: false }]
  };
  assert.deepEqual(scoreResponse(q, [true, true, false]), {
    correct: false, earned: 2, possible: 3
  });
});

test("scores matching independent of presentation order", () => {
  const q = { type: "matching", correctAnswer: { a: "2", b: "1" } };
  assert.equal(scoreResponse(q, { b: "1", a: "2" }).correct, true);
});
```

- [ ] **Step 2: Run tests and verify failure**

Run:

```powershell
node --test tests/question-renderer.test.mjs
```

Expected: FAIL because renderer exports do not exist.

- [ ] **Step 3: Implement safe rendering**

Escape all source text before inserting it into HTML. Implement dedicated branches for `mcq`, `multi-select`, `true-false`, `true-false-group`, `matching`, and `ordering`. Render source references and manual-review labels consistently.

- [ ] **Step 4: Run tests**

Run:

```powershell
node --test tests/question-renderer.test.mjs
```

Expected: PASS for all supported types, partial detail, XSS escaping, and answer review.

- [ ] **Step 5: Commit**

```powershell
git add study-website/js/question-renderer.js study-website/tests/question-renderer.test.mjs
git commit -m "feat: render and score all question types"
```

---

### Task 6: Implement Practice Mode

**Files:**
- Create: `study-website/js/quiz.js`
- Create: `study-website/tests/quiz.test.mjs`
- Modify: `study-website/js/app.js`
- Modify: `study-website/css/styles.css`

**Interfaces:**
- Consumes: filtered canonical questions, renderer functions, and storage operations.
- Produces: `createPracticeSession(config, questions)`, `answerPracticeQuestion(session, response)`, `movePractice(session, direction)`, and `finishPracticeSession(session)`.

- [ ] **Step 1: Write failing session tests**

```js
test("practice answer reveals feedback and records result", () => {
  const session = createPracticeSession(
    { count: "all", order: "original", shuffleChoices: false },
    [{ id: "q1", type: "mcq", options: ["A", "B"], correctAnswer: 1 }]
  );
  const next = answerPracticeQuestion(session, 0);
  assert.equal(next.answers.q1.correct, false);
  assert.equal(next.feedbackVisible, true);
});
```

- [ ] **Step 2: Run tests and verify failure**

Run:

```powershell
node --test tests/quiz.test.mjs
```

Expected: FAIL because practice functions do not exist.

- [ ] **Step 3: Implement setup, navigation, answers, bookmarks, and results**

Support all/source/type/topic/wrong/bookmarked/unanswered filters; 10/20/30/all counts; original/random order; optional choice shuffling; previous/next/skip; finish confirmation; progress display; and performance-based weak-topic results.

- [ ] **Step 4: Run tests and browser-check Practice Mode**

Expected: PASS for filtering, count limits, stable shuffled mappings, skipping, navigation, result totals, and session persistence.

- [ ] **Step 5: Commit**

```powershell
git add study-website/js/quiz.js study-website/js/app.js study-website/css/styles.css study-website/tests/quiz.test.mjs
git commit -m "feat: add complete practice mode"
```

---

### Task 7: Implement Mock Exam Mode

**Files:**
- Create: `study-website/js/exam.js`
- Create: `study-website/tests/exam.test.mjs`
- Modify: `study-website/js/app.js`
- Modify: `study-website/css/styles.css`

**Interfaces:**
- Produces: `createExam(config, questions, now)`, `answerExamQuestion(exam, response)`, `toggleExamFlag(exam, questionId)`, `getExamTimeRemaining(exam, now)`, `submitExam(exam, now)`, and `buildExamReview(exam)`.

- [ ] **Step 1: Write failing timer and submission tests**

```js
test("exam hides correctness until submission", () => {
  let exam = createExam({ count: 1, minutes: 10 }, [mcq], 1000);
  exam = answerExamQuestion(exam, 0);
  assert.equal(exam.answers.q1.correct, undefined);
  const result = submitExam(exam, 61000);
  assert.equal(result.correct, 0);
  assert.equal(result.timeTakenSeconds, 60);
});
```

- [ ] **Step 2: Run tests and verify failure**

Run:

```powershell
node --test tests/exam.test.mjs
```

Expected: FAIL because exam functions do not exist.

- [ ] **Step 3: Implement exam setup and state machine**

Support selected counts, optional timer, navigation grid, answered/unanswered markers, review flags, refresh recovery using an absolute end timestamp, confirmation before submit, unresolved-question exclusion, final score, percentage, correct/wrong/unanswered counts, time taken, source/topic breakdown, full review, retry wrong, and retake.

- [ ] **Step 4: Run tests and browser-check Exam Mode**

Expected: PASS for hidden feedback, timer recovery, unanswered scoring, flags, submission, review, retry, and retake.

- [ ] **Step 5: Commit**

```powershell
git add study-website/js/exam.js study-website/js/app.js study-website/css/styles.css study-website/tests/exam.test.mjs
git commit -m "feat: add mock exam mode"
```

---

### Task 8: Add Question Bank, Revision Summary, Mistakes, and Bookmarks

**Files:**
- Create: `study-website/js/revision.js`
- Create: `study-website/tests/revision.test.mjs`
- Modify: `study-website/js/app.js`
- Modify: `study-website/css/styles.css`

**Interfaces:**
- Produces: `buildRevisionCards(questions, state, filters)`, `getMistakeQuestions(questions, state)`, `getBookmarkedQuestions(questions, state)`, and `getWeakTopics(questions, state)`.

- [ ] **Step 1: Write failing revision tests**

```js
test("revision cards contain only official prompt and answer data", () => {
  const cards = buildRevisionCards([mcq], createDefaultState(), {});
  assert.deepEqual(Object.keys(cards[0]).sort(), [
    "answer", "id", "prompt", "sources", "topic"
  ]);
});

test("mistakes sort by incorrect attempts descending", () => {
  const result = getMistakeQuestions([q1, q2], {
    progress: { q1: { incorrectAttempts: 1 }, q2: { incorrectAttempts: 3 } }
  });
  assert.deepEqual(result.map((q) => q.id), ["q2", "q1"]);
});
```

- [ ] **Step 2: Run tests and verify failure**

Run:

```powershell
node --test tests/revision.test.mjs
```

Expected: FAIL because revision exports do not exist.

- [ ] **Step 3: Implement the four collection views**

Question Bank must search prompt text and filter by source/type/topic/status without showing answers in its list. Revision cards show only official prompt/answer/source content. Mistakes show selected answer, official answer, attempt count, and sources. Bookmarks allow removal, filtering, and focused practice.

- [ ] **Step 4: Run tests and browser-check all views**

Expected: PASS for privacy of answer lists, combined filters, sorting, weak-topic calculation, bookmark removal, and focused-session launch.

- [ ] **Step 5: Commit**

```powershell
git add study-website/js/revision.js study-website/js/app.js study-website/css/styles.css study-website/tests/revision.test.mjs
git commit -m "feat: add revision and review tools"
```

---

### Task 9: Complete dashboard, routing, theme, import/export, and shortcuts

**Files:**
- Modify: `study-website/js/app.js`
- Modify: `study-website/js/storage.js`
- Modify: `study-website/css/styles.css`
- Create: `study-website/tests/app.test.mjs`

**Interfaces:**
- Produces: `routeFromHash(hash)`, `shouldHandleShortcut(event)`, `downloadProgress(state)`, and `readProgressFile(file)`.

- [ ] **Step 1: Write failing routing and shortcut tests**

```js
test("shortcuts ignore editable controls", () => {
  assert.equal(shouldHandleShortcut({ target: { tagName: "INPUT" } }), false);
  assert.equal(shouldHandleShortcut({ target: { tagName: "TEXTAREA" } }), false);
  assert.equal(shouldHandleShortcut({ target: { tagName: "DIV", isContentEditable: true } }), false);
});

test("unknown hashes return dashboard", () => {
  assert.equal(routeFromHash("#/missing"), "dashboard");
});
```

- [ ] **Step 2: Run tests and verify failure**

Run:

```powershell
node --test tests/app.test.mjs
```

Expected: FAIL because app helpers do not exist.

- [ ] **Step 3: Implement application completion features**

Wire every navigation item and dashboard action. Persist theme preference. Add import validation, JSON export, destructive reset confirmation, toast feedback, empty states, resume last practice/exam, and keyboard shortcuts `1`-`4`, `T`, `F`, arrows, and `B`.

- [ ] **Step 4: Run all unit tests**

Run:

```powershell
node --test tests/*.test.mjs
```

Expected: all tests PASS.

- [ ] **Step 5: Commit**

```powershell
git add study-website/js/app.js study-website/js/storage.js study-website/css/styles.css study-website/tests/app.test.mjs
git commit -m "feat: complete dashboard and app controls"
```

---

### Task 10: Browser verification, documentation, and final audit

**Files:**
- Create: `study-website/tests/browser-check.mjs`
- Create: `study-website/README.md`
- Modify: `study-website/QUESTION_EXTRACTION_REPORT.md`

**Interfaces:**
- Consumes: the complete static website.
- Produces: reproducible browser verification and user-facing documentation.

- [ ] **Step 1: Write the browser smoke test**

The script must open the local site, capture `pageerror` and console errors, verify all navigation routes, answer MCQ and True/False items, bookmark a question, finish a practice session, submit an exam, toggle dark mode, export progress, reload to confirm persistence, import the exported state, and test a 390x844 mobile viewport.

```js
const errors = [];
page.on("pageerror", (error) => errors.push(error.message));
page.on("console", (message) => {
  if (message.type() === "error") errors.push(message.text());
});
assert.deepEqual(errors, []);
```

- [ ] **Step 2: Run the complete verification suite**

Run:

```powershell
python scripts/validate_questions.py
node --test study-website/tests/*.test.mjs
python -m http.server 8000 --directory study-website
node study-website/tests/browser-check.mjs
```

Expected: validator exits 0, every unit test passes, browser check passes, and there are zero console errors.

- [ ] **Step 3: Perform visual and responsive inspection**

Inspect dashboard, question bank, long MCQ, grouped True/False, matching, ordering, practice feedback, exam navigator, results, revision, mistakes, bookmarks, empty states, dialogs, light mode, dark mode, 390px mobile, 768px tablet, and 1440px desktop. Correct clipping, overlap, unreadable contrast, or inaccessible focus states.

- [ ] **Step 4: Complete documentation**

`README.md` must explain purpose, features, project structure, local server command, question schema, safe question corrections, LocalStorage key and export/import, deployment to Netlify/GitHub Pages/Vercel, test commands, and known limitations. Finalize the extraction report with measured totals and the exact manual-review list.

- [ ] **Step 5: Re-run verification after documentation and visual fixes**

Expected: all validation, unit, browser, and console checks still pass.

- [ ] **Step 6: Commit**

```powershell
git add study-website
git commit -m "docs: finish study website verification and guide"
```
