import assert from "node:assert/strict";
import test from "node:test";
import {
  BACKUP_STORAGE_KEY, PROJECT_ID, STATE_VERSION, STORAGE_KEY, clearActiveExam, createDefaultState,
  exportState, importState, loadState, markLessonComplete, recordAttempt, recordSessionSummary,
  resetState, saveState, setActiveExam, toggleBookmark,
} from "../js/storage.js";

function memoryStorage(initial = {}) {
  const values = new Map(Object.entries(initial));
  return { getItem: (key) => values.get(key) ?? null, setItem: (key, value) => values.set(key, String(value)), removeItem: (key) => values.delete(key), values };
}
const stamp = "2026-08-23T10:00:00.000Z";

test("creates a frozen OS default state and loads missing, corrupt, foreign, and unknown-version values safely", () => {
  const defaults = createDefaultState(stamp);
  assert.deepEqual(defaults, { version: STATE_VERSION, projectId: PROJECT_ID, updatedAt: stamp, lessonProgress: {}, questionProgress: {}, bookmarks: { lessonIds: [], questionIds: [] }, mistakes: {}, recentSessions: [], activeExam: null });
  assert.equal(Object.isFrozen(defaults), true);
  assert.deepEqual(loadState(memoryStorage(), stamp), defaults);
  const corrupt = memoryStorage({ [STORAGE_KEY]: "not json" });
  assert.equal(loadState(corrupt, stamp).projectId, PROJECT_ID);
  assert.equal(corrupt.getItem(BACKUP_STORAGE_KEY), "not json");
  const foreign = memoryStorage({ [STORAGE_KEY]: JSON.stringify({ ...defaults, projectId: "wrong" }) });
  assert.equal(loadState(foreign, stamp).projectId, PROJECT_ID);
  assert.match(foreign.getItem(BACKUP_STORAGE_KEY), /wrong/);
  const unknown = memoryStorage({ [STORAGE_KEY]: JSON.stringify({ ...defaults, version: 2 }) });
  assert.equal(loadState(unknown, stamp).version, STATE_VERSION);
  assert.match(unknown.getItem(BACKUP_STORAGE_KEY), /"version":2/);
});

test("saves and imports only a complete safe state and rejects malformed, duplicate, or executable-shaped payloads", () => {
  const defaults = createDefaultState(stamp);
  const storage = memoryStorage();
  const saved = saveState(defaults, storage);
  assert.deepEqual(saved, defaults);
  assert.deepEqual(importState(storage.getItem(STORAGE_KEY)), defaults);
  assert.equal(JSON.parse(exportState(defaults)).projectId, PROJECT_ID);
  assert.throws(() => importState(JSON.stringify({ ...defaults, extra: true })), /unknown|extra/i);
  assert.throws(() => importState(JSON.stringify({ ...defaults, bookmarks: { lessonIds: ["lesson-a", "lesson-a"], questionIds: [] } })), /duplicate/i);
  assert.throws(() => importState(JSON.stringify({ ...defaults, questionProgress: { "gq-one": { attempts: 1, correctAttempts: 0, incorrectAttempts: 1, lastAnswer: "1", lastAttemptAt: stamp, lastCorrect: false, lastCorrectAt: null } } })), /answer/i);
  assert.throws(() => importState(JSON.stringify({ ...defaults, questionProgress: { "gq-one": { attempts: -1, correctAttempts: 0, incorrectAttempts: 0, lastAnswer: 1, lastAttemptAt: stamp, lastCorrect: false, lastCorrectAt: null } } })), /negative/i);
  assert.throws(() => importState({ ...defaults, __proto__: { polluted: true } }), /plain|unknown/i);
});

test("records only finalized scoreable attempts without mutation and preserves historical mistakes after a correct answer", () => {
  const initial = createDefaultState(stamp);
  const ignored = recordAttempt(initial, { questionId: "gq-one", response: 1, correct: false, scored: false, finalized: true, at: stamp });
  assert.deepEqual(ignored.questionProgress, {});
  const wrong = recordAttempt(initial, { questionId: "gq-one", response: 1, correct: false, scored: true, finalized: true, at: stamp });
  const correct = recordAttempt(wrong, { questionId: "gq-one", response: 0, correct: true, scored: true, finalized: true, at: "2026-08-23T10:01:00.000Z" });
  assert.deepEqual(initial.questionProgress, {});
  assert.deepEqual(correct.questionProgress["gq-one"], { attempts: 2, correctAttempts: 1, incorrectAttempts: 1, lastAnswer: 0, lastAttemptAt: "2026-08-23T10:01:00.000Z", lastCorrect: true, lastCorrectAt: "2026-08-23T10:01:00.000Z" });
  assert.deepEqual(correct.mistakes["gq-one"], { count: 1, lastAttemptAt: stamp });
});

test("keeps lesson and question bookmarks separate, records lesson status, and persists only a safe active exam", () => {
  const initial = createDefaultState(stamp);
  const questionMarked = toggleBookmark(initial, "question", "gq-one", stamp);
  const lessonMarked = toggleBookmark(questionMarked, "lesson", "lesson-one", stamp);
  const lessonProgress = markLessonComplete(lessonMarked, "lesson-one", "completed", stamp, ["lesson-one"]);
  assert.deepEqual(lessonProgress.bookmarks, { lessonIds: ["lesson-one"], questionIds: ["gq-one"] });
  assert.deepEqual(lessonProgress.lessonProgress["lesson-one"], { status: "completed", lastVisitedAt: stamp });
  assert.throws(() => markLessonComplete(initial, "lesson-missing", "completed", stamp, ["lesson-one"]), /canonical/i);
  const activeExam = { id: "exam-1", projectId: PROJECT_ID, mode: "exam", status: "active", questionIds: ["gq-one"], answers: { "gq-one": { response: 1, answeredAt: 100 } }, index: 0, flagged: [], bookmarked: [], startedAt: 0, endsAt: 60_000 };
  const withExam = setActiveExam(lessonProgress, activeExam, stamp);
  assert.equal(withExam.activeExam.id, "exam-1");
  assert.deepEqual(clearActiveExam(withExam, stamp).activeExam, null);
  assert.throws(() => setActiveExam(initial, { ...activeExam, correctAnswer: 1 }, stamp), /unsafe|unknown/i);
});

test("records compact finalized sessions and resets only this site's progress and backup keys", () => {
  const storage = memoryStorage({ [STORAGE_KEY]: "saved", [BACKUP_STORAGE_KEY]: "backup", unrelated: "keep" });
  const state = recordSessionSummary(createDefaultState(stamp), { id: "practice-1", mode: "practice", finishedAt: stamp, scoreable: 2, correct: 1, incorrect: 1, unanswered: 0, percentage: 50, durationSeconds: 42 }, stamp);
  assert.equal(state.recentSessions.length, 1);
  assert.equal(state.recentSessions[0].id, "practice-1");
  assert.deepEqual(resetState(storage, stamp), createDefaultState(stamp));
  assert.equal(storage.getItem(STORAGE_KEY), null);
  assert.equal(storage.getItem(BACKUP_STORAGE_KEY), null);
  assert.equal(storage.getItem("unrelated"), "keep");
});
