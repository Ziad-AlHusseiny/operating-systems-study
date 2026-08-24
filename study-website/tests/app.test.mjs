import assert from "node:assert/strict";
import { readFile } from "node:fs/promises";
import test from "node:test";

const root = new URL("../", import.meta.url);
const appUrl = new URL("js/app.js", root);
const htmlUrl = new URL("index.html", root);
const cssUrl = new URL("css/styles.css", root);
const read = (url) => readFile(url, "utf8");

const loaded = await import(appUrl).catch((error) => ({ loadError: error }));
const { routeFromHash, escapeHtml, shouldHandleShortcut } = loaded;

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
});

test("visual CSS carries the approved responsive, accessible, bilingual token system", async () => {
  const css = await read(cssUrl);
  for (const token of ["#ffffff", "#f6f8fb", "#031b3d", "#0878f9", "#159947", "#d82424", "#b77900"]) assert.match(css, new RegExp(token, "i"));
  assert.match(css, /@media \(max-width: 1024px\)/);
  assert.match(css, /@media \(max-width: 900px\)/);
  assert.match(css, /@media \(max-width: 600px\)/);
  assert.match(css, /\[data-theme="dark"\]/);
  assert.match(css, /:focus-visible/);
  assert.match(css, /prefers-reduced-motion/);
  assert.match(css, /min-height:\s*44px/);
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
