import test from "node:test";
import assert from "node:assert/strict";
import { buildRevisionSummary, questionsForCollection } from "../js/revision.js";

const questions = [
  { id: "a", topic: "Backup", sources: [{ collection: "bank-105" }] },
  { id: "b", topic: "Backup", sources: [{ collection: "pretest-70" }] },
  { id: "c", topic: "Security", sources: [{ collection: "bank-105" }] },
];
const state = {
  progress: {
    a: { status: "wrong", incorrectAttempts: 2 },
    b: { status: "correct", incorrectAttempts: 1 },
  },
  bookmarks: ["c"],
};

test("builds revision sections from real progress", () => {
  const summary = buildRevisionSummary(questions, state);
  assert.equal(summary.mistakes.length, 1);
  assert.equal(summary.bookmarks.length, 1);
  assert.equal(summary.weakTopics[0].topic, "Backup");
});

test("selects collection questions without dropping shared entries", () => {
  assert.deepEqual(
    questionsForCollection(questions, "pretest-70").map((q) => q.id),
    ["b"]
  );
});
