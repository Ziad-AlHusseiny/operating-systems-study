import test from "node:test";
import assert from "node:assert/strict";
import { execFileSync } from "node:child_process";
import { readFile, stat } from "node:fs/promises";
import { fileURLToPath } from "node:url";

const dataUrl = new URL("../data/questions.json", import.meta.url);
const projectRoot = fileURLToPath(new URL("../../", import.meta.url));
const extractionReportUrl = new URL(
  "../QUESTION_EXTRACTION_REPORT.md",
  import.meta.url
);

async function loadData() {
  return JSON.parse(await readFile(dataUrl, "utf8"));
}

test("canonical bank has stable unique IDs and complete sources", async () => {
  const data = await loadData();
  const ids = data.questions.map((q) => q.id);
  const sources = data.questions.flatMap((q) => q.sources);

  assert.equal(new Set(ids).size, ids.length);
  assert.ok(data.questions.every((q) => q.prompt && q.sources.length >= 1));
  assert.equal(sources.filter((s) => s.collection === "bank-105").length, 105);
  assert.equal(sources.filter((s) => s.collection === "pretest-70").length, 70);
});

test("every scored question has a valid official answer", async () => {
  const data = await loadData();
  const supported = new Set([
    "mcq",
    "multi-select",
    "true-false-group",
    "matching",
    "ordering",
    "source-review",
  ]);

  for (const question of data.questions) {
    assert.ok(supported.has(question.type), `${question.id}: ${question.type}`);
    if (question.needsReview) continue;
    assert.notEqual(question.correctAnswer, null, question.id);
    if (question.type === "mcq") {
      assert.ok(Number.isInteger(question.correctAnswer), question.id);
      assert.ok(question.correctAnswer >= 0, question.id);
      assert.ok(question.correctAnswer < question.options.length, question.id);
    }
    if (question.type === "multi-select") {
      assert.ok(Array.isArray(question.correctAnswer), question.id);
      assert.ok(question.correctAnswer.length >= 2, question.id);
      assert.ok(question.correctAnswer.every((index) => index < question.options.length));
    }
  }
});

test("reviewed content preserves marked keys but clearly identifies unresolved items", async () => {
  const data = await loadData();
  const reviewed = data.questions.filter((question) => question.needsReview);
  for (const question of reviewed) {
    assert.ok(question.reviewNotes.trim().length > 0);
  }

  assert.deepEqual(
    reviewed.filter((question) => question.correctAnswer === null).map((question) => question.id),
    ["q-103"]
  );
  assert.deepEqual(
    reviewed.filter((question) => question.correctAnswer !== null).map((question) => question.id),
    ["q-015", "q-087", "q-093", "q-094"]
  );
});

test("question validation checks committed artifacts without rewriting them", async () => {
  const beforeData = await stat(dataUrl);
  const beforeReport = await stat(extractionReportUrl);
  const stdout = execFileSync("python", ["scripts/validate_questions.py", "--check"], {
    cwd: projectRoot,
    encoding: "utf8",
  });
  const afterData = await stat(dataUrl);
  const afterReport = await stat(extractionReportUrl);

  const report = await readFile(extractionReportUrl, "utf8");
  assert.equal(
    stdout.trim(),
    "Validated 103 canonical questions (5 need review); committed artifacts are current."
  );
  assert.equal(afterData.mtimeMs, beforeData.mtimeMs);
  assert.equal(afterReport.mtimeMs, beforeReport.mtimeMs);
  assert.match(report, /^## Arabic study guidance$/m);
  assert.match(report, /^## Arabic guidance maintenance$/m);
  assert.match(report, /python scripts\/build_explanations\.py/);
  assert.match(report, /content\/explanations-ar\/q079-103\.json/);
  assert.match(report, /never during an active Mock Exam/);
  assert.match(report, /Never select an answer for an unresolved official-source conflict/);
});
