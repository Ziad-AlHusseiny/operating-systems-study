import assert from "node:assert/strict";
import test from "node:test";
import { createDefaultState } from "../js/storage.js";
import { getBookmarkedLessons, getBookmarkedQuestions, getMistakeQuestions, getRevisionSummary } from "../js/revision.js";

const stamp = "2026-08-23T10:00:00.000Z";
function question(id, topic, objectiveId, overrides = {}) {
  const targets = ["prompt", "correctAnswer", "rationale", "options[0]", "options[1]", "options[2]", "options[3]", "distractorRationales[0]", "distractorRationales[1]", "distractorRationales[2]", "distractorRationales[3]"];
  return { id, origin: "generated", type: "mcq", prompt: `Prompt ${id}`, options: ["a", "b", "c", "d"], correctAnswer: 0, topic, learningObjectiveId: objectiveId, needsReview: false, review: { status: "validated" }, qualityState: "validated", reviewState: "unreviewed", duplicateDisposition: "retain", contentVersion: "1.0.0", reviewNotes: "", rationale: "Rationale", distractorRationales: ["one", "two", "three", "four"], sourceRefs: [{ sourceId: "os-lec-01" }], evidenceMap: targets.map((target, index) => ({ claimId: `${id}-${index}`, target, support: "direct", sourceRefs: [{ sourceId: "os-lec-01" }] })), ...overrides };
}
const lessons = [{ id: "lesson-one", moduleId: "module-one", title: "Processes" }, { id: "lesson-two", moduleId: "module-two", title: "Memory" }];
const modules = [{ id: "module-one", title: "Processes" }, { id: "module-two", title: "Memory" }];
const questions = [question("gq-one", "Processes", "objective-one"), question("gq-two", "Memory", "objective-two"), question("gq-review", "Memory", "objective-two", { needsReview: true })];
function state() {
  return {
    ...createDefaultState(stamp),
    lessonProgress: { "lesson-one": { status: "completed", lastVisitedAt: stamp }, "lesson-two": { status: "in-progress", lastVisitedAt: stamp } },
    questionProgress: {
      "gq-one": { attempts: 3, correctAttempts: 1, incorrectAttempts: 2, lastAnswer: 0, lastAttemptAt: "2026-08-23T10:02:00.000Z", lastCorrect: true, lastCorrectAt: "2026-08-23T10:02:00.000Z" },
      "gq-two": { attempts: 1, correctAttempts: 1, incorrectAttempts: 0, lastAnswer: 0, lastAttemptAt: stamp, lastCorrect: true, lastCorrectAt: stamp },
      "gq-review": { attempts: 9, correctAttempts: 0, incorrectAttempts: 9, lastAnswer: 0, lastAttemptAt: stamp, lastCorrect: false, lastCorrectAt: null },
      "gq-stale": { attempts: 9, correctAttempts: 0, incorrectAttempts: 9, lastAnswer: 0, lastAttemptAt: stamp, lastCorrect: false, lastCorrectAt: null },
    },
    mistakes: { "gq-one": { count: 2, lastAttemptAt: "2026-08-23T10:01:00.000Z" }, "gq-stale": { count: 9, lastAttemptAt: stamp } },
    bookmarks: { lessonIds: ["lesson-two", "lesson-stale"], questionIds: ["gq-two", "gq-stale"] },
    recentSessions: [{ id: "exam-1", mode: "exam", finishedAt: stamp, scoreable: 2, correct: 1, incorrect: 1, unanswered: 0, percentage: 50, durationSeconds: 60 }],
  };
}

test("summarizes completed lessons and scoreable attempts only, with a defined zero-attempt accuracy", () => {
  const summary = getRevisionSummary({ lessons, modules, questions }, state());
  assert.equal(summary.lessons.completed, 1);
  assert.equal(summary.lessons.total, 2);
  assert.deepEqual(summary.attempts, { answered: 4, correct: 2, incorrect: 2, accuracy: 50 });
  assert.equal(summary.mistakeCount, 2);
  assert.deepEqual(summary.bookmarks, { lessons: 1, questions: 1 });
  assert.equal(summary.recentSessions[0].id, "exam-1");
  assert.deepEqual(summary.weakTopics.map((item) => item.id), ["Processes"]);
  assert.equal(summary.revisionCards.length, 4);
  assert.equal(getRevisionSummary({ lessons, modules, questions }, createDefaultState(stamp)).attempts.accuracy, 0);
});

test("ranks historical mistakes by count then recency and reports mastered-after-mistake status", () => {
  const ranked = getMistakeQuestions(questions, state());
  assert.deepEqual(ranked.map((item) => item.id), ["gq-one"]);
  assert.equal(ranked[0].mistakeCount, 2);
  assert.equal(ranked[0].masteredAfterMistake, true);
});

test("uses the latest question attempt, not the historical mistake timestamp, to break mistake-count ties", () => {
  const left = question("gq-left", "Processes", "objective-one");
  const right = question("gq-right", "Memory", "objective-two");
  const current = {
    ...createDefaultState(stamp),
    questionProgress: {
      "gq-left": { attempts: 2, correctAttempts: 0, incorrectAttempts: 2, lastAnswer: 1, lastAttemptAt: "2026-08-23T10:01:00.000Z", lastCorrect: false, lastCorrectAt: null },
      "gq-right": { attempts: 2, correctAttempts: 1, incorrectAttempts: 1, lastAnswer: 0, lastAttemptAt: "2026-08-23T10:03:00.000Z", lastCorrect: true, lastCorrectAt: "2026-08-23T10:03:00.000Z" },
    },
    mistakes: {
      "gq-left": { count: 2, lastAttemptAt: "2026-08-23T10:05:00.000Z" },
      "gq-right": { count: 2, lastAttemptAt: "2026-08-23T10:00:00.000Z" },
    },
  };
  const ranked = getMistakeQuestions([left, right], current);
  assert.deepEqual(ranked.map((item) => item.id), ["gq-right", "gq-left"]);
  assert.equal(ranked[0].masteredAfterMistake, true);
});

test("returns only existing bookmarked questions and lessons in canonical order", () => {
  const current = state();
  assert.deepEqual(getBookmarkedQuestions(questions, current).map((item) => item.id), ["gq-two"]);
  assert.deepEqual(getBookmarkedLessons(lessons, current).map((item) => item.id), ["lesson-two"]);
});
