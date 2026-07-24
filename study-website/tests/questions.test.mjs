import test from "node:test";
import assert from "node:assert/strict";
import {
  filterQuestions,
  shuffleChoices,
  shuffleQuestions,
} from "../js/questions.js";

test("filters by source, type, and status together", () => {
  const questions = [
    { id: "q1", type: "mcq", sources: [{ collection: "bank-105" }] },
    { id: "q2", type: "true-false-group", sources: [{ collection: "pretest-70" }] },
  ];
  const result = filterQuestions(questions, {
    source: "bank-105",
    type: "mcq",
    status: "unanswered",
    progress: {},
  });
  assert.deepEqual(result.map((question) => question.id), ["q1"]);
});

test("search is case-insensitive and includes topic text", () => {
  const questions = [
    { id: "q1", prompt: "Configure a drive", topic: "Storage" },
    { id: "q2", prompt: "Manage an account", topic: "Accounts" },
  ];
  assert.deepEqual(
    filterQuestions(questions, { search: "STORAGE" }).map((question) => question.id),
    ["q1"]
  );
});

test("choice shuffling remaps a single correct answer", () => {
  const question = {
    id: "q1",
    type: "mcq",
    options: ["A", "B", "C"],
    correctAnswer: 1,
  };
  const values = [0.9, 0.1];
  const shuffled = shuffleChoices(question, () => values.shift());
  assert.equal(shuffled.options[shuffled.correctAnswer], "B");
  assert.equal(shuffled.choiceOrder[shuffled.correctAnswer], 1);
  assert.deepEqual(question.options, ["A", "B", "C"]);
});

test("question shuffling returns a copy", () => {
  const questions = [{ id: "q1" }, { id: "q2" }, { id: "q3" }];
  const result = shuffleQuestions(questions, () => 0);
  assert.notEqual(result, questions);
  assert.deepEqual(questions.map((question) => question.id), ["q1", "q2", "q3"]);
});
