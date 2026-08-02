# Arabic Question Explanations Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Add reviewed Arabic translations, medium ChatGPT-style explanations, and revision notes for all 103 canonical questions, expose them through a dedicated page and answer-review flows, and publish the verified feature to GitHub Pages.

**Architecture:** Author explanation content in four independently reviewable JSON source files under `content/explanations-ar/`. A Python builder validates and merges them into the single delivered `study-website/data/explanations-ar.json`. A focused browser module loads, validates, searches, and filters explanations; the existing app composes it with canonical questions without changing official source data.

**Tech Stack:** Python 3 standard library, HTML5, CSS3, vanilla JavaScript ES modules, JSON, LocalStorage, Node.js built-in test runner, Playwright CLI for browser QA, GitHub Actions Pages deployment.

## Global Constraints

- Cover all 103 canonical questions in `study-website/data/questions.json`.
- Store generated guidance separately from official PDF question data.
- Use natural Arabic with simple technical wording and keep useful Windows commands and product names in English.
- Give each question a complete Arabic translation, two or three short Arabic explanation paragraphs, and one short revision note.
- Explain the official answer without changing it or claiming the explanation came from the PDFs.
- Translate every answer-bearing statement or item for grouped, matching, ordering, and multi-select questions.
- Do not choose an answer for the unresolved source-conflict item.
- Preserve plain HTML, CSS, vanilla JavaScript, JSON, and LocalStorage with no frontend package dependency or build step.
- Escape all rendered content and fail softly if explanation data cannot load.
- Preserve existing Practice, Exam, Question Bank, Revision, saved progress, light/dark themes, and responsive behavior.

---

### Task 1: Add the explanation source schema and deterministic builder

**Files:**
- Create: `content/explanations-ar/README.md`
- Create: `scripts/build_explanations.py`
- Create: `study-website/tests/explanations-data.test.mjs`
- Produce: `study-website/data/explanations-ar.json`

**Interfaces:**
- Consumes: `study-website/data/questions.json` and `content/explanations-ar/q001-026.json`, `q027-052.json`, `q053-078.json`, `q079-103.json`.
- Produces: `build_payload(question_path: Path, part_paths: list[Path]) -> dict` and one delivered payload shaped as `{version, language, generatedStudyGuidance, explanations}`.

- [ ] **Step 1: Write the failing coverage and schema tests**

Create `study-website/tests/explanations-data.test.mjs` with tests that read both canonical files and assert exact ID equality, Arabic text presence, paragraph counts, non-empty notes, and conflict handling:

```js
import test from "node:test";
import assert from "node:assert/strict";
import { readFile } from "node:fs/promises";

const questions = JSON.parse(
  await readFile(new URL("../data/questions.json", import.meta.url), "utf8")
).questions;
const payload = JSON.parse(
  await readFile(new URL("../data/explanations-ar.json", import.meta.url), "utf8")
);
const arabic = /[\u0600-\u06ff]/;

test("Arabic explanations cover every canonical question exactly once", () => {
  const questionIds = questions.map((question) => question.id).sort();
  const explanationIds = Object.keys(payload.explanations).sort();
  assert.equal(explanationIds.length, 103);
  assert.deepEqual(explanationIds, questionIds);
});

test("every explanation has complete Arabic study content", () => {
  for (const [id, entry] of Object.entries(payload.explanations)) {
    assert.match(entry.translation, arabic, `${id} translation`);
    assert.ok([2, 3].includes(entry.explanation.length), `${id} paragraphs`);
    assert.ok(entry.explanation.every((paragraph) => arabic.test(paragraph)), id);
    assert.match(entry.note, arabic, `${id} note`);
  }
});

test("the unresolved item explains the conflict without selecting an answer", () => {
  const item = payload.explanations["q-103"];
  const combined = [item.translation, ...item.explanation, item.note].join(" ");
  assert.match(combined, /تعارض|اختلاف/);
  assert.doesNotMatch(combined, /الإجابة الصحيحة هي/);
});
```

- [ ] **Step 2: Run the data test and verify RED**

Run from the repository root:

```powershell
node --test study-website/tests/explanations-data.test.mjs
```

Expected: FAIL because `study-website/data/explanations-ar.json` does not exist.

- [ ] **Step 3: Document the exact authoring schema**

Create `content/explanations-ar/README.md` with this required entry shape and rules:

```json
{
  "q-001": {
    "translation": "ترجمة عربية كاملة للسؤال والعناصر المؤثرة في الإجابة.",
    "explanation": [
      "فقرة قصيرة تشرح الفكرة الأساسية بلغة واضحة.",
      "فقرة قصيرة تربط الفكرة بالإجابة الرسمية وتوضح سبب صحتها."
    ],
    "note": "ملاحظة مراجعة قصيرة وسهلة التذكر."
  }
}
```

Document that keys must be within the file's assigned range, fields must contain Arabic, explanations must have two or three paragraphs, and `q-103` must remain unresolved.

- [ ] **Step 4: Implement the deterministic builder**

Create `scripts/build_explanations.py` using only `json`, `re`, and `pathlib`. Implement:

```python
ARABIC = re.compile(r"[\u0600-\u06ff]")

def validate_entry(question_id: str, entry: dict) -> list[str]:
    errors = []
    if not isinstance(entry.get("translation"), str) or not ARABIC.search(entry["translation"]):
        errors.append(f"{question_id}: translation must contain Arabic")
    paragraphs = entry.get("explanation")
    if not isinstance(paragraphs, list) or len(paragraphs) not in (2, 3):
        errors.append(f"{question_id}: explanation must have 2 or 3 paragraphs")
    elif not all(isinstance(value, str) and ARABIC.search(value) for value in paragraphs):
        errors.append(f"{question_id}: every explanation paragraph must contain Arabic")
    if not isinstance(entry.get("note"), str) or not ARABIC.search(entry["note"]):
        errors.append(f"{question_id}: note must contain Arabic")
    return errors

def build_payload(question_path: Path, part_paths: list[Path]) -> dict:
    questions = json.loads(question_path.read_text(encoding="utf-8"))["questions"]
    expected_ids = {question["id"] for question in questions}
    merged = {}
    for part_path in part_paths:
        for question_id, entry in json.loads(part_path.read_text(encoding="utf-8")).items():
            if question_id in merged:
                raise ValueError(f"duplicate explanation ID: {question_id}")
            merged[question_id] = entry
    if set(merged) != expected_ids:
        missing = sorted(expected_ids - set(merged))
        unknown = sorted(set(merged) - expected_ids)
        raise ValueError(f"coverage mismatch: missing={missing}, unknown={unknown}")
    errors = [error for question_id, entry in merged.items() for error in validate_entry(question_id, entry)]
    if errors:
        raise ValueError("\n".join(errors))
    return {
        "version": 1,
        "language": "ar",
        "generatedStudyGuidance": True,
        "explanations": dict(sorted(merged.items())),
    }
```

The CLI writes UTF-8, indented JSON to `study-website/data/explanations-ar.json` and prints the validated count.

- [ ] **Step 5: Commit the schema, builder, and intentionally failing test**

```powershell
git add content/explanations-ar/README.md scripts/build_explanations.py study-website/tests/explanations-data.test.mjs
git commit -m "test: define Arabic explanation coverage"
```

---

### Task 2: Author and review explanations for q-001 through q-026

**Files:**
- Create: `content/explanations-ar/q001-026.json`

**Interfaces:**
- Consumes: canonical questions `q-001` through `q-026`, including every option, statement, item, official answer, source, and review flag.
- Produces: exactly 26 JSON entries matching the Task 1 schema.

- [ ] **Step 1: Extract a review worksheet for the assigned range**

Run and review the printed canonical objects directly:

```powershell
node -e "const d=require('./study-website/data/questions.json'); console.log(JSON.stringify(d.questions.slice(0,26),null,2))"
```

- [ ] **Step 2: Author all 26 entries**

For every question, translate the complete prompt and answer-bearing subparts. Write two or three short Arabic paragraphs: concept first, official-answer reasoning second, and alternative elimination only when useful. End with one concise revision note. Keep commands such as `ipconfig`, product names, file systems, and Windows UI labels in English with Arabic context.

- [ ] **Step 3: Run the range validator**

```powershell
python -c "import json; p=json.load(open('content/explanations-ar/q001-026.json',encoding='utf-8')); assert list(p)==[f'q-{i:03d}' for i in range(1,27)]; assert all(len(v['explanation']) in (2,3) for v in p.values()); print(len(p))"
```

Expected: `26`.

- [ ] **Step 4: Review content against official answers**

For each ID, compare the Arabic reasoning to `correctAnswer` and its type-specific option, statement, match, or order. Correct any answer mismatch, missing translated subpart, overclaim, or untranslated exam-relevant label.

- [ ] **Step 5: Commit the first content range**

```powershell
git add content/explanations-ar/q001-026.json
git commit -m "content: explain questions 1 through 26 in Arabic"
```

---

### Task 3: Author and review explanations for q-027 through q-052

**Files:**
- Create: `content/explanations-ar/q027-052.json`

**Interfaces:**
- Consumes: canonical questions `q-027` through `q-052`.
- Produces: exactly 26 JSON entries matching the Task 1 schema.

- [ ] **Step 1: Extract the exact canonical range**

```powershell
node -e "const d=require('./study-website/data/questions.json'); console.log(JSON.stringify(d.questions.slice(26,52),null,2))"
```

- [ ] **Step 2: Author complete Arabic content for all 26 IDs**

Apply the Global Constraints to each prompt, all type-specific subparts, the official answer reasoning, and the revision note. Keep technical tokens in English where learners must recognize the Windows label or command.

- [ ] **Step 3: Run the exact range check**

```powershell
python -c "import json; p=json.load(open('content/explanations-ar/q027-052.json',encoding='utf-8')); assert list(p)==[f'q-{i:03d}' for i in range(27,53)]; assert all(len(v['explanation']) in (2,3) for v in p.values()); print(len(p))"
```

Expected: `26`.

- [ ] **Step 4: Review each explanation against its canonical correct answer**

Reject content that explains a different option, omits a grouped statement, presents generated guidance as source text, or adds unrelated factual claims.

- [ ] **Step 5: Commit the second content range**

```powershell
git add content/explanations-ar/q027-052.json
git commit -m "content: explain questions 27 through 52 in Arabic"
```

---

### Task 4: Author and review explanations for q-053 through q-078

**Files:**
- Create: `content/explanations-ar/q053-078.json`

**Interfaces:**
- Consumes: canonical questions `q-053` through `q-078`.
- Produces: exactly 26 JSON entries matching the Task 1 schema.

- [ ] **Step 1: Extract the exact canonical range**

```powershell
node -e "const d=require('./study-website/data/questions.json'); console.log(JSON.stringify(d.questions.slice(52,78),null,2))"
```

- [ ] **Step 2: Author complete Arabic content for all 26 IDs**

Use two or three short paragraphs per entry and finish with one exam-focused note. Translate all comparison rows, matching descriptions, and true/false statements that affect scoring.

- [ ] **Step 3: Run the exact range check**

```powershell
python -c "import json; p=json.load(open('content/explanations-ar/q053-078.json',encoding='utf-8')); assert list(p)==[f'q-{i:03d}' for i in range(53,79)]; assert all(len(v['explanation']) in (2,3) for v in p.values()); print(len(p))"
```

Expected: `26`.

- [ ] **Step 4: Review each explanation against the canonical correct answer**

Check option indices, multi-select sets, true/false arrays, and matching maps. Correct any Arabic wording that reverses a condition or makes a partial-credit question sound single-answer.

- [ ] **Step 5: Commit the third content range**

```powershell
git add content/explanations-ar/q053-078.json
git commit -m "content: explain questions 53 through 78 in Arabic"
```

---

### Task 5: Author q-079 through q-103 and merge the delivered dataset

**Files:**
- Create: `content/explanations-ar/q079-103.json`
- Create: `study-website/data/explanations-ar.json`
- Modify: `study-website/QUESTION_EXTRACTION_REPORT.md`

**Interfaces:**
- Consumes: canonical questions `q-079` through `q-103` plus all four content part files.
- Produces: exactly 25 source entries and one validated delivered dataset covering all 103 IDs.

- [ ] **Step 1: Extract the exact final range**

```powershell
node -e "const d=require('./study-website/data/questions.json'); console.log(JSON.stringify(d.questions.slice(78,103),null,2))"
```

- [ ] **Step 2: Author all 25 entries with explicit conflict handling**

Write normal content for `q-079` through `q-102`. For `q-103`, translate the prompt, explain that the pre-test highlights `Differential` while the 105-question bank marks `Incremental`, state that the website does not choose between conflicting official sources, and use a note telling the learner to review both cited pages.

- [ ] **Step 3: Validate the final range**

```powershell
python -c "import json; p=json.load(open('content/explanations-ar/q079-103.json',encoding='utf-8')); assert list(p)==[f'q-{i:03d}' for i in range(79,104)]; assert all(len(v['explanation']) in (2,3) for v in p.values()); assert 'تعارض' in ' '.join(p['q-103']['explanation']); print(len(p))"
```

Expected: `25`.

- [ ] **Step 4: Build and validate the merged dataset**

```powershell
python scripts/build_explanations.py
node --test study-website/tests/explanations-data.test.mjs
```

Expected: builder prints `Validated 103 Arabic explanations.` and all data tests PASS.

- [ ] **Step 5: Document generated guidance separately from official extraction**

Add an `Arabic study guidance` section to `QUESTION_EXTRACTION_REPORT.md` stating that 103 generated translations/explanations live in a separate file, are not official PDF explanations, and do not resolve `q-103`.

- [ ] **Step 6: Commit the final content and merged output**

```powershell
git add content/explanations-ar/q079-103.json study-website/data/explanations-ar.json study-website/QUESTION_EXTRACTION_REPORT.md
git commit -m "content: complete Arabic explanations for all questions"
```

---

### Task 6: Implement explanation loading, validation, search, and filtering

**Files:**
- Create: `study-website/js/explanations.js`
- Create: `study-website/tests/explanations.test.mjs`

**Interfaces:**
- Consumes: the delivered explanation payload and canonical question array.
- Produces: `loadExplanations(url)`, `validateExplanationPayload(payload, questions)`, `searchExplanationEntries(questions, explanations, filters)`, and `getExplanation(explanations, questionId)`.

- [ ] **Step 1: Write failing module tests**

Test exact schema rejection, unknown/missing IDs, Arabic search, English search, source/topic/type filtering, and safe missing lookup:

```js
test("search includes Arabic translation, explanation, and note", () => {
  const result = searchExplanationEntries(questions, explanations, { search: "نسخ احتياطي" });
  assert.deepEqual(result.map((entry) => entry.question.id), ["q-007"]);
});

test("missing explanations return null", () => {
  assert.equal(getExplanation({}, "q-999"), null);
});
```

- [ ] **Step 2: Run the module tests and verify RED**

```powershell
node --test study-website/tests/explanations.test.mjs
```

Expected: FAIL because `js/explanations.js` does not exist.

- [ ] **Step 3: Implement the focused module**

`loadExplanations` fetches JSON and checks HTTP status. `validateExplanationPayload` enforces version `1`, language `ar`, object shape, canonical ID equality, and field types. `searchExplanationEntries` combines the English prompt with Arabic translation, paragraphs, and note, then applies canonical source/topic/type filters. `getExplanation` returns an entry or `null`.

- [ ] **Step 4: Run the focused and complete unit suites**

```powershell
node --test study-website/tests/explanations.test.mjs
node --test study-website/tests/*.test.mjs
```

Expected: all tests PASS.

- [ ] **Step 5: Commit the explanation module**

```powershell
git add study-website/js/explanations.js study-website/tests/explanations.test.mjs
git commit -m "feat: load and filter Arabic explanations"
```

---

### Task 7: Add safe Arabic explanation rendering

**Files:**
- Modify: `study-website/js/question-renderer.js`
- Modify: `study-website/tests/question-renderer.test.mjs`

**Interfaces:**
- Consumes: one canonical question and its explanation entry or `null`.
- Produces: `renderArabicExplanation(question, explanation, options = {}) -> string`.

- [ ] **Step 1: Write failing renderer tests**

Add tests asserting `lang="ar"`, `dir="rtl"`, translation, two paragraphs, note, generated-guidance label, conflict label, missing state, and escaping of `<script>` in every field.

- [ ] **Step 2: Run the renderer test and verify RED**

```powershell
node --test study-website/tests/question-renderer.test.mjs
```

Expected: FAIL because `renderArabicExplanation` is not exported.

- [ ] **Step 3: Implement semantic safe rendering**

Render an `<aside class="arabic-explanation" lang="ar" dir="rtl">` with separate translation, official-answer, explanation, and note regions. Use the existing `escapeHtml` for every source and generated string. If the explanation is `null`, render a short unavailable message without throwing. If `question.needsReview`, show a conflict warning instead of a correct-answer heading.

- [ ] **Step 4: Run renderer and full tests**

```powershell
node --test study-website/tests/question-renderer.test.mjs
node --test study-website/tests/*.test.mjs
```

Expected: all tests PASS.

- [ ] **Step 5: Commit the renderer**

```powershell
git add study-website/js/question-renderer.js study-website/tests/question-renderer.test.mjs
git commit -m "feat: render Arabic study explanations safely"
```

---

### Task 8: Build the dedicated Question Explanations page

**Files:**
- Modify: `study-website/index.html`
- Modify: `study-website/js/app.js`
- Modify: `study-website/css/styles.css`
- Create: `study-website/tests/explanations-view.test.mjs`

**Interfaces:**
- Consumes: `app.questions`, `app.explanations`, explanation filters, bookmarks, `searchExplanationEntries`, and `renderArabicExplanation`.
- Produces: the `#/explanations` route, `explanationsMarkup()`, an incremental `visibleExplanationCount`, and filter/bookmark interactions.

- [ ] **Step 1: Write failing view-helper tests**

Add and test `limitExplanationEntries(entries, visibleCount = 15)` and `increaseVisibleCount(current, total, step = 15)`. Assert the first helper returns only the visible slice and the second increases by 15 without exceeding the filtered total.

- [ ] **Step 2: Run the view tests and verify RED**

```powershell
node --test study-website/tests/explanations-view.test.mjs
```

Expected: FAIL because the view helpers and route do not exist.

- [ ] **Step 3: Add navigation and startup loading**

Add `Question Explanations` to the desktop sidebar. Load explanations in parallel with the question bank during startup, store a non-fatal `explanationsError`, and route `#/explanations` to the new page. Keep the existing application usable if the explanation request fails.

- [ ] **Step 4: Implement the explanation page**

Add English/Arabic search, source/topic/type filters, result count, 15-entry initial slice, `Show more` control, bookmark actions, generated-guidance notice, and cards containing original prompt plus `renderArabicExplanation` output.

- [ ] **Step 5: Add professional responsive styling**

Use the current design tokens. Add an open-list card treatment, visible separation between English source content and RTL guidance, a success-accent official-answer block, a blue explanation block, a warning-accent revision note, readable Arabic line height, dark-mode tokens, 1440px two-column metadata alignment, and 390px single-column flow without horizontal scrolling.

- [ ] **Step 6: Run view and complete unit tests**

```powershell
node --test study-website/tests/explanations-view.test.mjs
node --test study-website/tests/*.test.mjs
```

Expected: all tests PASS.

- [ ] **Step 7: Commit the dedicated page**

```powershell
git add study-website/index.html study-website/js/app.js study-website/css/styles.css study-website/tests/explanations-view.test.mjs
git commit -m "feat: add Arabic question explanations page"
```

---

### Task 9: Integrate explanations into Practice, Question Bank, and Exam Review

**Files:**
- Modify: `study-website/js/app.js`
- Modify: `study-website/css/styles.css`
- Modify: `study-website/tests/explanations-view.test.mjs`

**Interfaces:**
- Consumes: `renderArabicExplanation`, current question/session answer, and `app.explanations`.
- Produces: reusable `explanationDisclosure(question, {open})` included only after answer visibility is allowed.

- [ ] **Step 1: Add failing visibility tests**

Test that Practice feedback includes the disclosure after checking an answer, Exam question markup excludes it before submission, Exam Results include it, Question Bank includes it only inside the opened details content, and missing data renders a soft unavailable state.

- [ ] **Step 2: Run the integration tests and verify RED**

```powershell
node --test study-website/tests/explanations-view.test.mjs
```

Expected: FAIL because review flows do not include explanations.

- [ ] **Step 3: Implement disclosure integration**

Use native `<details>` with an `Arabic Explanation` summary and correct `aria` behavior. Practice adds it after `renderAnswerReview`; Exam Results adds it inside each review item; Question Bank adds it after the official answer inside the existing closed question details. Never render it in an active Exam question.

- [ ] **Step 4: Style the disclosure states**

Match existing borders, focus states, spacing, and dark theme. Ensure nested details remain readable and touch targets are at least 44px high on mobile.

- [ ] **Step 5: Run the full unit suite**

```powershell
node --test study-website/tests/*.test.mjs
```

Expected: all tests PASS.

- [ ] **Step 6: Commit review-flow integration**

```powershell
git add study-website/js/app.js study-website/css/styles.css study-website/tests/explanations-view.test.mjs
git commit -m "feat: connect Arabic explanations to answer reviews"
```

---

### Task 10: Complete documentation, browser QA, and GitHub Pages deployment

**Files:**
- Modify: `study-website/README.md`
- Modify: `study-website/QUESTION_EXTRACTION_REPORT.md`
- Verify: `.github/workflows/pages.yml`

**Interfaces:**
- Consumes: the complete local site and existing `origin/master` GitHub Pages workflow.
- Produces: verified local and public explanation pages and a documented content-maintenance workflow.

- [ ] **Step 1: Update user and maintainer documentation**

Document the `Question Explanations` page, Arabic search/filter behavior, generated-guidance label, content-part files, builder command, validation tests, conflict policy, and how to correct an explanation without changing official question data.

- [ ] **Step 2: Run fresh deterministic validation**

```powershell
python scripts/validate_questions.py
python scripts/build_explanations.py
node --check study-website/js/app.js
node --check study-website/js/explanations.js
node --check study-website/js/question-renderer.js
node --test study-website/tests/*.test.mjs
git diff --check
```

Expected: both builders exit `0`, exactly 103 explanations validate, all tests PASS, and diff check is clean.

- [ ] **Step 3: Run local browser QA**

Serve `study-website` on localhost and use Playwright CLI. Verify page title, non-blank content, zero relevant console errors, explanation route, Arabic search, source/topic/type filters, show-more behavior, bookmark persistence, Practice disclosure after answering, no active-Exam leakage, Exam Review disclosure, dark mode, 1440x1000 desktop, and 390x844 mobile.

- [ ] **Step 4: Perform visual fidelity comparison**

Compare the updated dashboard and explanation page against `docs/design-concepts/dashboard.png` and the existing rendered visual system. Use `view_image` on the accepted concept and latest desktop/mobile screenshots. Record at least five checks: sidebar density, page-header scale, white/navy/blue palette, card borders/radii, Arabic typography/RTL spacing, and mobile bottom-nav behavior. Fix every material mismatch.

- [ ] **Step 5: Commit documentation and final visual fixes**

```powershell
git add study-website/README.md study-website/QUESTION_EXTRACTION_REPORT.md study-website/css/styles.css
git commit -m "docs: finish Arabic explanation guidance"
```

- [ ] **Step 6: Push and monitor deployment**

```powershell
git push origin master
$pagesRunId = gh run list --repo Ziad-AlHusseiny/its-device-configuration-study --workflow pages.yml --limit 1 --json databaseId --jq '.[0].databaseId'
gh run watch $pagesRunId --repo Ziad-AlHusseiny/its-device-configuration-study --interval 5 --exit-status
```

Expected: GitHub Pages build and deploy jobs both conclude `success`.

- [ ] **Step 7: Verify the public deployment**

Verify HTTP `200` for:

```text
https://ziad-alhusseiny.github.io/its-device-configuration-study/
https://ziad-alhusseiny.github.io/its-device-configuration-study/data/explanations-ar.json
```

Confirm the live JSON contains 103 entries and use browser QA on `#/explanations` to confirm Arabic cards, filtering, Practice integration, and mobile layout work on the deployed site.
