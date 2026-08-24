import assert from "node:assert/strict";
import { readFile } from "node:fs/promises";
import test from "node:test";

const root = new URL("../", import.meta.url);
const appUrl = new URL("js/app.js", root);
const htmlUrl = new URL("index.html", root);
const cssUrl = new URL("css/styles.css", root);
const read = (url) => readFile(url, "utf8");

const loaded = await import(appUrl).catch((error) => ({ loadError: error }));
const {
  routeFromHash,
  escapeHtml,
  shouldHandleShortcut,
  navigationRenderDecision,
  getSetupSummary,
  getPracticeQuestionView,
  renderLessonGroup,
  lessonSectionLanguage,
  getDashboardCoverage,
  trapDialogFocus,
  shortcutAnswerDecision,
  questionRecordRoute,
  navigationCurrentState,
} = loaded;

async function payload(name) {
  return JSON.parse(await read(new URL(`data/${name}.json`, root)));
}

function assertHelper(value, name) {
  assert.equal(typeof value, "function", `${name} must be exported as a testable UI decision helper`);
  return typeof value === "function";
}

function shortcutEvent(overrides = {}) {
  return {
    defaultPrevented: false,
    ctrlKey: false,
    metaKey: false,
    altKey: false,
    key: "ArrowRight",
    target: { tagName: "DIV", isContentEditable: false, closest: () => null },
    ...overrides,
  };
}

test("route parser resolves all canonical routes and the bank compatibility alias", () => {
  const names = [
    "dashboard", "material", "questions", "explanations", "practice", "exam",
    "revision", "mistakes", "bookmarks", "settings",
  ];
  for (const name of names) assert.deepEqual(routeFromHash(`#/${name}`), { name });
  assert.deepEqual(routeFromHash("#/bank"), { name: "questions" });
});

test("route parser normalizes lesson IDs and safely rejects invalid hashes", () => {
  assert.deepEqual(routeFromHash("#/lesson/lesson-os-ch01-part1"), { name: "lesson", id: "lesson-os-ch01-part1" });
  assert.deepEqual(routeFromHash("#/lesson/os-ch01-part1"), { name: "lesson", id: "lesson-os-ch01-part1" });
  for (const hash of ["", "#", "#/unknown", "#/lesson", "#/lesson/%3Cbad%3E", "#/lesson/a?x=1"]) {
    assert.equal(routeFromHash(hash).name, "not-found");
  }
});

test("route parser and record-route helper preserve canonical Question Bank and Explanation targets", () => {
  if (!assertHelper(questionRecordRoute, "questionRecordRoute") || !assertHelper(navigationCurrentState, "navigationCurrentState")) return;
  const id = "gq-os-ch05-part3-010";
  assert.equal(questionRecordRoute("questions", id), "#/questions/gq-os-ch05-part3-010");
  assert.equal(questionRecordRoute("explanations", id), "#/explanations/gq-os-ch05-part3-010");
  assert.deepEqual(routeFromHash(questionRecordRoute("questions", id)), { name: "questions", id });
  assert.deepEqual(routeFromHash(questionRecordRoute("explanations", id)), { name: "explanations", id });
  assert.equal(routeFromHash("#/questions/not-a-question").name, "not-found");
  assert.deepEqual(navigationCurrentState({ name: "lesson", id: "lesson-os-ch01-part1" }), { desktop: "material", mobile: "material", more: false });
  assert.deepEqual(navigationCurrentState({ name: "explanations", id }), { desktop: "explanations", mobile: null, more: true });
});

test("HTML escaping protects all dangerous characters and safely stringifies values", () => {
  assert.equal(escapeHtml(`&<>"'`), "&amp;&lt;&gt;&quot;&#39;");
  assert.equal(escapeHtml(42), "42");
  assert.equal(escapeHtml(null), "");
  assert.equal(escapeHtml(undefined), "");
});

test("session shortcuts ignore controls, modifiers, and prevented events", () => {
  for (const target of ["INPUT", "TEXTAREA", "SELECT", "BUTTON", "A"]) {
    assert.equal(shouldHandleShortcut(shortcutEvent({ target: { tagName: target, isContentEditable: false, closest: () => null } })), false);
  }
  assert.equal(shouldHandleShortcut(shortcutEvent({ defaultPrevented: true })), false);
  assert.equal(shouldHandleShortcut(shortcutEvent({ ctrlKey: true })), false);
  assert.equal(shouldHandleShortcut(shortcutEvent({ metaKey: true })), false);
  assert.equal(shouldHandleShortcut(shortcutEvent({ altKey: true })), false);
  assert.equal(shouldHandleShortcut(shortcutEvent({ target: { tagName: "DIV", isContentEditable: true, closest: () => null } })), false);
  assert.equal(shouldHandleShortcut(shortcutEvent({ target: { tagName: "SPAN", isContentEditable: false, closest: (selector) => selector === "[contenteditable='true']" ? {} : null } })), false);
});

test("session shortcuts allow documented keys only with ordinary page focus", () => {
  for (const key of ["1", "2", "3", "4", "t", "T", "f", "F", "ArrowLeft", "ArrowRight", "b", "B", "s", "S"]) {
    assert.equal(shouldHandleShortcut(shortcutEvent({ key })), true, key);
  }
  assert.equal(shouldHandleShortcut(shortcutEvent({ key: "q" })), false);
});

test("same-route navigation requests an immediate render for a newly active Practice or Mock Exam", () => {
  if (!assertHelper(navigationRenderDecision, "navigationRenderDecision")) return;
  assert.deepEqual(navigationRenderDecision("#/practice", "#/practice"), { setHash: false, renderNow: true });
  assert.deepEqual(navigationRenderDecision("#/exam", "#/exam"), { setHash: false, renderNow: true });
  assert.deepEqual(navigationRenderDecision("#/dashboard", "#/practice"), { setHash: true, renderNow: false });
});

test("Practice answer shortcuts explicitly ignore already answered questions while preserving Mock Exam dispatch", () => {
  if (!assertHelper(shortcutAnswerDecision, "shortcutAnswerDecision")) return;
  const practice = Object.freeze({ answers: Object.freeze({ "question-1": Object.freeze({ response: 1, correct: false }) }) });
  const before = structuredClone(practice);
  assert.equal(shortcutAnswerDecision("practice", practice, "question-1", 2), "ignore");
  assert.equal(shortcutAnswerDecision("practice", { answers: {} }, "question-1", 2), "practice");
  assert.equal(shortcutAnswerDecision("exam", { answers: { "question-1": { response: 1 } } }, "question-1", 2), "exam");
  assert.equal(shortcutAnswerDecision("practice", practice, "question-1", undefined), "none");
  assert.deepEqual(practice, before);
});

test("setup eligibility summary uses Task 6 filters, states selected scope, and blocks empty or oversized starts", async () => {
  if (!assertHelper(getSetupSummary, "getSetupSummary")) return;
  const [course, questions] = await Promise.all([payload("course"), payload("questions")]);
  const setup = { moduleId: "all", lessonId: "all", topic: "all", type: "all", difficulty: "all", bloomLevel: "all", order: "original", count: "1", minutes: "30" };
  const ready = getSetupSummary("practice", questions.questions, setup, course, {});
  assert.equal(ready.scopeCount, questions.questions.length);
  assert.equal(ready.eligibleCount, questions.questions.filter((question) => question.origin === "generated").length);
  assert.equal(ready.requestedCount, 1);
  assert.equal(ready.minutes, null);
  assert.equal(ready.canStart, true);
  const oversized = getSetupSummary("practice", questions.questions, { ...setup, count: String(ready.eligibleCount + 1) }, course, {});
  assert.equal(oversized.canStart, false);
  assert.match(oversized.message, /only .* eligible/i);
  const invalidCount = getSetupSummary("practice", questions.questions, { ...setup, count: "0" }, course, {});
  assert.equal(invalidCount.canStart, false);
  assert.match(invalidCount.message, /positive question count/i);
  const empty = getSetupSummary("exam", questions.questions, { ...setup, topic: "does-not-exist" }, course, {});
  assert.equal(empty.eligibleCount, 0);
  assert.equal(empty.canStart, false);
});

test("revisited Practice answers are locked and reconstruct their original stored feedback without mutation", () => {
  if (!assertHelper(getPracticeQuestionView, "getPracticeQuestionView")) return;
  const answer = Object.freeze({ response: 1, answeredAt: 100, valid: true, scored: true, correct: false, correctAnswer: 2 });
  const session = Object.freeze({ answers: Object.freeze({ "question-1": answer }) });
  const question = Object.freeze({ id: "question-1", rationale: "Stored rationale", sourceRefs: Object.freeze([{ sourceId: "source-1", location: 4 }]) });
  const before = structuredClone(session);
  const view = getPracticeQuestionView(session, question, { translation: "إرشاد", explanation: ["تفصيل"], note: "راجع" });
  assert.equal(view.locked, true);
  assert.equal(view.response, 1);
  assert.deepEqual(view.feedback, { questionId: "question-1", response: 1, answeredAt: 100, valid: true, scored: true, correct: false, correctAnswer: 2, rationale: "Stored rationale", sourceRefs: [{ sourceId: "source-1", location: 4 }], explanation: { translation: "إرشاد", explanation: ["تفصيل"], note: "راجع" } });
  assert.deepEqual(session, before);
});

test("lesson mistake guidance renders misconception, correction, and citations while preserving ordinary body groups", async () => {
  if (!assertHelper(renderLessonGroup, "renderLessonGroup")) return;
  const lessons = await payload("lessons");
  const sourceMistake = lessons.lessons.flatMap((lesson) => lesson.materialSections).flatMap((section) => section.mistakes || []).find((entry) => entry.misconception && entry.correction);
  const mistakes = renderLessonGroup("Common mistakes", [sourceMistake], () => '<span class="citation">Source citation</span>');
  assert.match(mistakes, new RegExp(sourceMistake.misconception));
  assert.match(mistakes, new RegExp(sourceMistake.correction));
  assert.match(mistakes, /Source citation/);
  assert.doesNotMatch(mistakes, /undefined|null/);
  const summary = renderLessonGroup("Summary", [{ body: "A source-backed summary.", sourceRefs: [] }]);
  assert.match(summary, /A source-backed summary\./);
});

test("generated Arabic lesson guidance gets Arabic boundaries without applying them to English source sections", async () => {
  if (!assertHelper(lessonSectionLanguage, "lessonSectionLanguage")) return;
  const lessons = await payload("lessons");
  const sections = lessons.lessons.flatMap((lesson) => lesson.materialSections);
  const generated = sections.find((section) => section.origin === "generated" && section.generatedStudyGuidance === true);
  const source = sections.find((section) => section.origin === "source" && section.generatedStudyGuidance === false);
  assert.deepEqual(lessonSectionLanguage(generated), { lang: "ar", dir: "rtl", className: "material-section arabic" });
  assert.deepEqual(lessonSectionLanguage(source), { lang: "en", dir: "ltr", className: "material-section" });
});

test("dashboard coverage is measured from the payload and reports the seven modules and twenty-one lessons", async () => {
  if (!assertHelper(getDashboardCoverage, "getDashboardCoverage")) return;
  const [course, lessons] = await Promise.all([payload("course"), payload("lessons")]);
  assert.deepEqual(getDashboardCoverage({ modules: course.modules, lessons: lessons.lessons }), { modules: 7, lessons: 21 });
});

test("dialog focus trap cycles Tab and Shift+Tab through dialog controls", () => {
  if (!assertHelper(trapDialogFocus, "trapDialogFocus")) return;
  const focused = [];
  const controls = ["first", "middle", "last"].map((id) => ({ id, focus: () => focused.push(id) }));
  const tab = { key: "Tab", shiftKey: false, target: controls[2], prevented: false, preventDefault() { this.prevented = true; } };
  assert.equal(trapDialogFocus(tab, controls), true);
  assert.equal(tab.prevented, true);
  assert.deepEqual(focused, ["first"]);
  const shiftTab = { key: "Tab", shiftKey: true, target: controls[0], prevented: false, preventDefault() { this.prevented = true; } };
  assert.equal(trapDialogFocus(shiftTab, controls), true);
  assert.equal(shiftTab.prevented, true);
  assert.deepEqual(focused, ["first", "last"]);
  assert.equal(trapDialogFocus({ key: "Tab", shiftKey: false, target: controls[1], preventDefault() { throw new Error("should not trap middle control"); } }, controls), false);
});

test("static shell identifies Operating Systems Study and provides semantic loading and recovery hooks", async () => {
  const html = await read(htmlUrl);
  assert.match(html, /<title>Operating Systems Study<\/title>/);
  assert.match(html, /name="description" content="A bilingual, source-backed Operating Systems study and exam website\."/);
  for (const tag of ["<aside", "<nav", "<header", "<main"]) assert.match(html, new RegExp(tag));
  assert.match(html, /id="app-status"[^>]*aria-live="polite"/);
  assert.match(html, /id="app-loading"/);
  assert.match(html, /id="app-error"/);
  assert.match(html, /id="dialog-root"/);
  assert.match(html, /id="toast-region"[^>]*aria-live="polite"/);
  assert.match(html, /id="progress-import"[^>]*type="file"/);
  assert.doesNotMatch(html, /\bon\w+\s*=/i);
  assert.doesNotMatch(html, /ITS Device|ITS Study|Device Configuration/i);
});

test("static shell contains desktop, mobile, and More navigation routes", async () => {
  const html = await read(htmlUrl);
  for (const route of ["dashboard", "material", "practice", "exam", "questions", "explanations", "revision", "mistakes", "bookmarks", "settings"]) {
    assert.match(html, new RegExp(`#/${route}`));
  }
  assert.match(html, /id="mobile-navigation"/);
  assert.match(html, /More/);
  assert.match(html, /class="more-menu"[^>]*data-more-menu/);
});

test("visual CSS carries the approved responsive, accessible, bilingual token system", async () => {
  const css = await read(cssUrl);
  for (const token of ["#ffffff", "#f6f8fb", "#031b3d", "#0878f9", "#159947", "#d82424", "#b77900"]) assert.match(css, new RegExp(token, "i"));
  assert.match(css, /@media \(max-width: 1024px\)/);
  assert.match(css, /@media \(max-width: 900px\)/);
  assert.match(css, /@media \(max-width: 600px\)/);
  assert.match(css, /\[data-theme="dark"\]/);
  assert.match(css, /:focus-visible/);
  assert.match(css, /\.theme-switch input:focus-visible/);
  assert.match(css, /\.answer-row:has\(input:focus-visible\)[^{]*\{[^}]*outline:/);
  assert.match(css, /prefers-reduced-motion/);
  assert.match(css, /min-height:\s*44px/);
  assert.match(css, /@media \(max-width: 1024px\)[\s\S]*?\.navigator button\s*\{[^}]*min-height:\s*44px/);
  assert.match(css, /\[dir="rtl"\]/);
  assert.match(css, /overflow-wrap:\s*anywhere/);
  assert.doesNotMatch(css, /@import|fonts\.googleapis|linear-gradient|radial-gradient/i);
});

test("application source integrates only current Task 6 modules and protects active exams", async () => {
  const source = await read(appUrl);
  for (const module of ["data.js", "questions.js", "quiz.js", "exam.js", "storage.js", "revision.js"]) assert.match(source, new RegExp(module.replace(".", "\\.")));
  for (const obsolete of ["explanations-view", "question-renderer", "statistics", "bank-page", "pretest-page"]) assert.doesNotMatch(source, new RegExp(obsolete, "i"));
  for (const route of ["dashboard", "material", "lesson", "questions", "explanations", "practice", "exam", "revision", "mistakes", "bookmarks", "settings"]) assert.match(source, new RegExp(`render${route[0].toUpperCase()}${route.slice(1)}`));
  const activeExam = source.match(/function renderActiveExam[\s\S]*?(?=\nfunction |\nexport |\nconst )/)?.[0] ?? "";
  assert.notEqual(activeExam, "");
  for (const forbidden of ["correctAnswer", "rationale", "explanation", "translation", "correctness"]) assert.doesNotMatch(activeExam, new RegExp(forbidden));
});

test("README and starter describe a deployment-subpath-safe static OS site", async () => {
  const [readme, starter] = await Promise.all([read(new URL("README.md", root)), read(new URL("../START_WEBSITE.bat", root))]);
  assert.match(readme, /Operating Systems Study/);
  assert.match(readme, /python -m http\.server/);
  assert.match(readme, /hash route|HashRouter|#\/dashboard/i);
  assert.match(starter, /study-website/);
  assert.match(starter, /python -m http\.server/);
  assert.doesNotMatch(`${readme}\n${starter}`, /ITS Device|bank-page|pretest-page/i);
});
