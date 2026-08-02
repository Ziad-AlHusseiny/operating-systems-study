import test from "node:test";
import assert from "node:assert/strict";
import {
  STORAGE_KEY,
  createDefaultState,
  exportState,
  importState,
  loadState,
  normalizeStateForQuestions,
  recordAttempt,
  resetState,
  saveState,
  toggleBookmark,
} from "../js/storage.js";
import {
  getDashboardStats,
  getPerformanceBreakdown,
  getSessionStats,
} from "../js/statistics.js";

function memoryStorage(initial = {}) {
  const values = new Map(Object.entries(initial));
  return {
    getItem: (key) => values.get(key) ?? null,
    setItem: (key, value) => values.set(key, String(value)),
    removeItem: (key) => values.delete(key),
  };
}

test("recordAttempt keeps history and latest status", () => {
  const state = createDefaultState();
  const next = recordAttempt(state, {
    questionId: "q1",
    selectedAnswer: 2,
    correct: false,
    at: "2026-07-24T12:00:00Z",
  });
  assert.equal(next.progress.q1.incorrectAttempts, 1);
  assert.equal(next.progress.q1.status, "wrong");
  assert.equal(next.history.length, 1);
  assert.equal(state.history.length, 0);
});

test("save and load preserve versioned progress", () => {
  const storage = memoryStorage();
  const state = toggleBookmark(createDefaultState(), "q3");
  saveState(state, storage);
  assert.deepEqual(loadState(storage), state);
  assert.ok(storage.getItem(STORAGE_KEY));
});

test("damaged saved state safely falls back to defaults", () => {
  const storage = memoryStorage({ [STORAGE_KEY]: "{broken" });
  assert.deepEqual(loadState(storage), createDefaultState());
});

test("import validates schema before returning state", () => {
  const state = toggleBookmark(createDefaultState(), "q1");
  assert.deepEqual(importState(exportState(state)), state);
  assert.throws(() => importState('{"version":99}'), /version/i);
  assert.throws(
    () =>
      importState(
        '{"version":1,"progress":{},"bookmarks":"q1","history":[],"sessions":[],"exams":[]}'
      ),
    /bookmarks/i
  );
});

test("reset removes saved state", () => {
  const storage = memoryStorage({ [STORAGE_KEY]: "{}" });
  assert.deepEqual(resetState(storage), createDefaultState());
  assert.equal(storage.getItem(STORAGE_KEY), null);
});

test("dashboard accuracy uses answered questions only", () => {
  const stats = getDashboardStats(
    [{ id: "q1" }, { id: "q2" }, { id: "q3" }],
    {
      progress: {
        q1: { status: "correct" },
        q2: { status: "wrong" },
      },
    }
  );
  assert.equal(stats.accuracy, 50);
  assert.equal(stats.completion, 67);
  assert.equal(stats.answered, 2);
});

test("performance breakdown groups by topic", () => {
  const result = getPerformanceBreakdown(
    [
      { id: "q1", topic: "Networking" },
      { id: "q2", topic: "Networking" },
      { id: "q3", topic: "Security" },
    ],
    {
      progress: {
        q1: { status: "correct" },
        q2: { status: "wrong" },
        q3: { status: "correct" },
      },
    },
    "topic"
  );
  assert.deepEqual(result, [
    { name: "Networking", total: 2, answered: 2, correct: 1, wrong: 1, accuracy: 50 },
    { name: "Security", total: 1, answered: 1, correct: 1, wrong: 0, accuracy: 100 },
  ]);
});

test("unscored source-review answers remain in skipped totals", () => {
  const stats = getSessionStats(
    ["q1"],
    { q1: { correct: null, possible: 0 } },
    10
  );
  assert.deepEqual(
    { correct: stats.correct, wrong: stats.wrong, skipped: stats.skipped },
    { correct: 0, wrong: 0, skipped: 1 }
  );
});

test("normalizes legacy review scoring while preserving unrelated progress and bookmarks", () => {
  const questions = [
    { id: "q-scored", needsReview: false },
    { id: "q-review", needsReview: true, reviewNotes: "Review the marked key." },
  ];
  const legacySession = {
    mode: "practice",
    questionIds: ["q-scored", "q-review"],
    answers: {
      "q-scored": { response: 1, correct: true, earned: 1, possible: 1 },
      "q-review": { response: 2, correct: false, earned: 0, possible: 1 },
    },
    questionOverrides: {
      "q-review": { id: "q-review", correctAnswer: 2, needsReview: false },
    },
    stats: { correct: 1, wrong: 1, skipped: 0, answered: 2, accuracy: 50, durationSeconds: 30 },
  };
  const legacy = {
    ...createDefaultState(),
    progress: {
      "q-scored": { status: "correct", attempts: 1 },
      "q-review": { status: "wrong", attempts: 3, incorrectAttempts: 2 },
    },
    bookmarks: ["q-scored", "q-review"],
    history: [
      { questionId: "q-scored", correct: true },
      { questionId: "q-review", selectedAnswer: 2, correct: false },
    ],
    sessions: [legacySession],
    exams: [{ ...legacySession, mode: "exam" }],
    activePractice: legacySession,
    activeExam: { ...legacySession, mode: "exam" },
  };

  const normalized = normalizeStateForQuestions(legacy, questions);

  assert.deepEqual(normalized.progress, {
    "q-scored": { status: "correct", attempts: 1 },
  });
  assert.deepEqual(normalized.bookmarks, ["q-scored", "q-review"]);
  assert.equal(normalized.history[0].correct, true);
  assert.equal(normalized.history[1].correct, null);
  assert.equal(normalized.history[1].selectedAnswer, 2);
  assert.equal(normalized.activeExam, null);
  for (const session of [normalized.sessions[0], normalized.exams[0], normalized.activePractice]) {
    assert.deepEqual(session.answers["q-review"], {
      response: 2,
      correct: null,
      earned: 0,
      possible: 0,
    });
    assert.equal(session.questionOverrides["q-review"].needsReview, true);
    assert.equal(session.questionOverrides["q-review"].reviewNotes, "Review the marked key.");
    assert.deepEqual(
      {
        correct: session.stats.correct,
        wrong: session.stats.wrong,
        skipped: session.stats.skipped,
        answered: session.stats.answered,
        accuracy: session.stats.accuracy,
      },
      { correct: 1, wrong: 0, skipped: 1, answered: 1, accuracy: 100 }
    );
  }
  assert.equal(legacy.progress["q-review"].status, "wrong");
});

test("normalizes imported version-one legacy progress against current review flags", () => {
  const reviewIds = ["q-015", "q-087", "q-093", "q-094", "q-103"];
  const legacy = {
    ...createDefaultState(),
    progress: Object.fromEntries([
      ...reviewIds.map((questionId) => [questionId, { status: "correct", attempts: 1 }]),
      ["q-001", { status: "wrong", attempts: 1 }],
    ]),
    bookmarks: [...reviewIds, "q-001"],
  };

  const imported = importState(JSON.stringify(legacy));
  const normalized = normalizeStateForQuestions(imported, [
    ...reviewIds.map((id) => ({ id, needsReview: true })),
    { id: "q-001", needsReview: false },
  ]);

  assert.equal(normalized.version, 1);
  for (const questionId of reviewIds) {
    assert.equal(normalized.progress[questionId], undefined);
  }
  assert.equal(normalized.progress["q-001"].status, "wrong");
  assert.deepEqual(normalized.bookmarks, [...reviewIds, "q-001"]);
});

test("statistics ignore stale scored progress for current review questions", () => {
  const questions = [
    { id: "q-scored", topic: "Shared", needsReview: false },
    { id: "q-review", topic: "Shared", needsReview: true },
  ];
  const state = {
    progress: {
      "q-scored": { status: "correct" },
      "q-review": { status: "wrong" },
    },
  };

  assert.deepEqual(getDashboardStats(questions, state), {
    uniqueTotal: 2,
    total: 1,
    answered: 1,
    correct: 1,
    wrong: 0,
    unanswered: 0,
    accuracy: 100,
    completion: 100,
  });
  assert.deepEqual(getPerformanceBreakdown(questions, state, "topic"), [
    { name: "Shared", total: 1, answered: 1, correct: 1, wrong: 0, accuracy: 100 },
  ]);
});

test("dashboard statistics separate 103 unique questions from 98 scoreable questions", () => {
  const questions = Array.from({ length: 103 }, (_, index) => ({
    id: `q-${String(index + 1).padStart(3, "0")}`,
    needsReview: index >= 98,
  }));

  const stats = getDashboardStats(questions, { progress: {} });

  assert.equal(stats.uniqueTotal, 103);
  assert.equal(stats.total, 98);
  assert.equal(stats.unanswered, 98);
  assert.equal(stats.completion, 0);
});
