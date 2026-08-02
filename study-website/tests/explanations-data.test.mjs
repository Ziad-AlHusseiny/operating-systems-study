import test from "node:test";
import assert from "node:assert/strict";
import { spawnSync } from "node:child_process";
import { readFile } from "node:fs/promises";

const questions = JSON.parse(
  await readFile(new URL("../data/questions.json", import.meta.url), "utf8")
).questions;
const payload = JSON.parse(
  await readFile(new URL("../data/explanations-ar.json", import.meta.url), "utf8")
);
const arabic = /[\u0600-\u06ff]/;

test("builder reports the required Arabic delivery count", () => {
  const result = spawnSync("python", ["scripts/build_explanations.py"], {
    cwd: new URL("../../", import.meta.url),
    encoding: "utf8",
  });

  assert.equal(result.status, 0, result.stderr);
  assert.equal(result.stdout.trim(), "Validated 103 Arabic explanations.");
});

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
