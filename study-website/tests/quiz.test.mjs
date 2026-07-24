import test from "node:test";
import assert from "node:assert/strict";
import {
  answerSessionQuestion,
  createSession,
  finishSession,
  moveSession,
} from "../js/quiz.js";

const questions = [
  { id: "a", type: "mcq", topic: "One", correctAnswer: 1 },
  { id: "b", type: "mcq", topic: "Two", correctAnswer: 0 },
  { id: "c", type: "mcq", topic: "One", correctAnswer: 2 },
];

test("creates a bounded practice session", () => {
  const session = createSession(questions, { count: 2, mode: "practice" }, () => 0.9, 1000);
  assert.equal(session.questionIds.length, 2);
  assert.equal(session.mode, "practice");
  assert.equal(session.startedAt, 1000);
});

test("records and navigates answers without losing prior work", () => {
  let session = createSession(questions, { count: 3, mode: "practice", shuffle: false }, Math.random, 1000);
  session = answerSessionQuestion(session, questions[0], 1, 1200);
  session = moveSession(session, 1);
  assert.equal(session.index, 1);
  assert.equal(session.answers.a.correct, true);
});

test("finishes a session with correct, wrong, and skipped totals", () => {
  let session = createSession(questions, { count: 3, shuffle: false }, Math.random, 1000);
  session = answerSessionQuestion(session, questions[0], 1, 1200);
  session = answerSessionQuestion(session, questions[1], 1, 1400);
  const result = finishSession(session, 3000);
  assert.deepEqual(
    { correct: result.stats.correct, wrong: result.stats.wrong, skipped: result.stats.skipped },
    { correct: 1, wrong: 1, skipped: 1 }
  );
});
