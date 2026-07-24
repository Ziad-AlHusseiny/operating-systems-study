import test from "node:test";
import assert from "node:assert/strict";
import {
  STORAGE_KEY,
  createDefaultState,
  exportState,
  importState,
  loadState,
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
