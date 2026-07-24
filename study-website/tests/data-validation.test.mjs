import test from "node:test";
import assert from "node:assert/strict";
import { readFile } from "node:fs/promises";

const dataUrl = new URL("../data/questions.json", import.meta.url);

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

test("unresolved content is clearly reported instead of guessed", async () => {
  const data = await loadData();
  for (const question of data.questions.filter((q) => q.needsReview)) {
    assert.equal(question.correctAnswer, null);
    assert.ok(question.reviewNotes.trim().length > 0);
  }
});
