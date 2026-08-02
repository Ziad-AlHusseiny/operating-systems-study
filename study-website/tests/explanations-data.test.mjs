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
  assert.match(combined, /ØªØ¹Ø§Ø±Ø¶|Ø§Ø®ØªÙ„Ø§Ù/);
  assert.doesNotMatch(combined, /Ø§Ù„Ø¥Ø¬Ø§Ø¨Ø© Ø§Ù„ØµØ­ÙŠØ­Ø© Ù‡ÙŠ/);
});
