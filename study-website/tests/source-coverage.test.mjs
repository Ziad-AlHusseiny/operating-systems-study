import test from "node:test";
import assert from "node:assert/strict";
import { readFile } from "node:fs/promises";

test("raw extraction covers both official collections", async () => {
  const rawUrl = new URL("../../extraction/raw-questions.json", import.meta.url);
  const raw = JSON.parse(await readFile(rawUrl, "utf8"));

  assert.equal(raw.filter((q) => q.sourceId === "bank-105").length, 105);
  assert.equal(raw.filter((q) => q.sourceId === "pretest-70").length, 70);
  assert.ok(raw.every((q) => q.sourcePage > 0 && q.sourceQuestion > 0));
  assert.ok(raw.every((q) => q.rawText.trim().length > 0));
  assert.ok(
    raw
      .filter((q) => q.sourceId === "pretest-70")
      .every((q) => Array.isArray(q.answerRegions) && q.answerRegions.length > 0)
  );
});
