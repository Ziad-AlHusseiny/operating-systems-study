import { isExamEligible, isScoreable, isValidResponse } from "./questions.js";

export const STORAGE_KEY = "os-study-progress-v1";
export const BACKUP_STORAGE_KEY = "os-study-progress-v1-backup";
export const STATE_VERSION = 1;
export const PROJECT_ID = "operating-systems-study";

const STATE_KEYS = ["version", "projectId", "updatedAt", "lessonProgress", "questionProgress", "bookmarks", "mistakes", "recentSessions", "activeExam"];
const PROGRESS_KEYS = ["attempts", "correctAttempts", "incorrectAttempts", "lastAnswer", "lastAttemptAt", "lastCorrect", "lastCorrectAt"];
const SESSION_KEYS = ["id", "mode", "finishedAt", "scoreable", "correct", "incorrect", "unanswered", "percentage", "durationSeconds"];
const EXAM_KEYS = ["id", "projectId", "mode", "status", "questionIds", "answers", "index", "flagged", "bookmarked", "startedAt", "endsAt", "emptyReason"];

function isPlainObject(value) {
  if (!value || typeof value !== "object" || Array.isArray(value)) return false;
  const prototype = Object.getPrototypeOf(value);
  return prototype === Object.prototype || prototype === null;
}

function clone(value) {
  return structuredClone(value);
}

function freeze(value, seen = new Set()) {
  if (!value || typeof value !== "object" || seen.has(value)) return value;
  seen.add(value);
  for (const item of Object.values(value)) freeze(item, seen);
  return Object.freeze(value);
}

function assertKeys(value, keys, label) {
  if (!isPlainObject(value)) throw new Error(`${label} must be a plain object.`);
  const actual = Object.keys(value);
  const extra = actual.find((key) => !keys.includes(key));
  const missing = keys.find((key) => !Object.hasOwn(value, key));
  if (extra) throw new Error(`${label} contains an unknown field: ${extra}.`);
  if (missing) throw new Error(`${label} is missing ${missing}.`);
}

function isIsoTimestamp(value) {
  if (typeof value !== "string" || !/^\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}\.\d{3}Z$/.test(value)) return false;
  const date = new Date(value);
  return !Number.isNaN(date.valueOf()) && date.toISOString() === value;
}

function assertTimestamp(value, label) {
  if (!isIsoTimestamp(value)) throw new Error(`${label} must be an ISO UTC timestamp.`);
}

function assertIds(values, label, prefix) {
  if (!Array.isArray(values) || !values.every((id) => typeof id === "string" && id.startsWith(prefix))) {
    throw new Error(`${label} contains an invalid ID.`);
  }
  if (new Set(values).size !== values.length) throw new Error(`${label} contains duplicate IDs.`);
}

function isQuestionId(id) {
  return typeof id === "string" && (id.startsWith("q-") || id.startsWith("gq-"));
}

function recordValues(records, label) {
  if (Array.isArray(records)) return records;
  if (records instanceof Map || records instanceof Set) return [...records.values()];
  if (records && typeof records === "object") return Object.values(records);
  throw new Error(`Canonical ${label} records are invalid.`);
}

function canonicalContext(canonical) {
  if (canonical === undefined || canonical === null) return { lessonIds: null, questionById: null, course: null };
  const source = Array.isArray(canonical) || canonical instanceof Set ? { lessons: canonical } : canonical;
  if (!isPlainObject(source)) throw new Error("Canonical records are invalid.");
  const lessonRecords = source.lessons ?? source.lessonById ?? source.lessonIds;
  const questionRecords = source.questions ?? source.questionById;
  const lessonIds = lessonRecords === undefined ? null : new Set(recordValues(lessonRecords, "lesson").map((lesson) => typeof lesson === "string" ? lesson : lesson?.id));
  if (lessonIds && [...lessonIds].some((id) => typeof id !== "string" || !id.startsWith("lesson-"))) throw new Error("Canonical lesson records are invalid.");
  if (questionRecords === undefined) return { lessonIds, questionById: null, course: source.course ?? null };
  const questionById = new Map();
  for (const question of recordValues(questionRecords, "question")) {
    if (!isPlainObject(question) || !isQuestionId(question.id) || questionById.has(question.id)) throw new Error("Canonical question records are invalid.");
    questionById.set(question.id, question);
  }
  return { lessonIds, questionById, course: source.course ?? null };
}

function assertCanonicalLesson(id, canonical) {
  if (typeof id !== "string" || !id.startsWith("lesson-")) throw new Error("A canonical lesson ID is required.");
  if (canonical.lessonIds && !canonical.lessonIds.has(id)) throw new Error(`Lesson ${id} is not a current canonical lesson.`);
}

function assertCanonicalQuestion(id, canonical) {
  if (!isQuestionId(id)) throw new Error("A canonical question ID is required.");
  const question = canonical.questionById?.get(id);
  if (canonical.questionById && !question) throw new Error(`Question ${id} is not a current canonical question.`);
  return question;
}

function assertQuestionIds(values, label) {
  if (!Array.isArray(values) || !values.every(isQuestionId)) throw new Error(`${label} contains an invalid ID.`);
  if (new Set(values).size !== values.length) throw new Error(`${label} contains duplicate IDs.`);
}

function isAnswer(value) {
  return typeof value === "boolean" || (Number.isInteger(value) && value >= 0);
}

function assertProgress(progress, canonical) {
  if (!isPlainObject(progress)) throw new Error("Question progress is invalid.");
  for (const [id, entry] of Object.entries(progress)) {
    const question = assertCanonicalQuestion(id, canonical);
    assertKeys(entry, PROGRESS_KEYS, `Question progress for ${id}`);
    for (const field of ["attempts", "correctAttempts", "incorrectAttempts"]) {
      if (!Number.isInteger(entry[field]) || entry[field] < 0) throw new Error("Question progress has a negative counter.");
    }
    if (entry.correctAttempts + entry.incorrectAttempts !== entry.attempts) throw new Error("Question progress counters do not match attempts.");
    if (!isAnswer(entry.lastAnswer)) throw new Error("Question progress has an invalid answer payload.");
    if (question && !isValidResponse(question, entry.lastAnswer)) throw new Error("Question progress has an invalid answer payload.");
    assertTimestamp(entry.lastAttemptAt, "Question progress timestamp");
    if (typeof entry.lastCorrect !== "boolean") throw new Error("Question progress lastCorrect is invalid.");
    if (entry.lastCorrectAt !== null) assertTimestamp(entry.lastCorrectAt, "Question progress correct timestamp");
  }
}

function assertLessons(progress, canonical) {
  if (!isPlainObject(progress)) throw new Error("Lesson progress is invalid.");
  for (const [id, entry] of Object.entries(progress)) {
    assertCanonicalLesson(id, canonical);
    assertKeys(entry, ["status", "lastVisitedAt"], `Lesson progress for ${id}`);
    if (!["completed", "in-progress"].includes(entry.status)) throw new Error("Lesson progress has an invalid status.");
    assertTimestamp(entry.lastVisitedAt, "Lesson progress timestamp");
  }
}

function assertMistakes(mistakes, canonical) {
  if (!isPlainObject(mistakes)) throw new Error("Mistakes are invalid.");
  for (const [id, entry] of Object.entries(mistakes)) {
    assertCanonicalQuestion(id, canonical);
    if (!isPlainObject(entry) || Object.keys(entry).length !== 2 || !Object.hasOwn(entry, "count") || !Object.hasOwn(entry, "lastAttemptAt")) {
      throw new Error("Mistakes are invalid.");
    }
    if (!Number.isInteger(entry.count) || entry.count < 1) throw new Error("Mistakes have a negative counter.");
    assertTimestamp(entry.lastAttemptAt, "Mistake timestamp");
  }
}

function assertSession(summary) {
  assertKeys(summary, SESSION_KEYS, "Recent session");
  if (typeof summary.id !== "string" || !summary.id || !["practice", "exam"].includes(summary.mode)) throw new Error("Recent session is invalid.");
  assertTimestamp(summary.finishedAt, "Recent session timestamp");
  for (const field of ["scoreable", "correct", "incorrect", "unanswered", "percentage", "durationSeconds"]) {
    if (!Number.isFinite(summary[field]) || summary[field] < 0) throw new Error("Recent session has invalid totals.");
  }
}

function assertActiveExam(exam, canonical) {
  if (exam === null) return;
  if (!isPlainObject(exam)) throw new Error("Active exam must be a plain object.");
  const extra = Object.keys(exam).find((key) => !EXAM_KEYS.includes(key));
  const missing = EXAM_KEYS.filter((key) => key !== "emptyReason").find((key) => !Object.hasOwn(exam, key));
  if (extra) throw new Error(`Active exam contains an unknown field: ${extra}.`);
  if (missing) throw new Error(`Active exam is missing ${missing}.`);
  if (exam.projectId !== PROJECT_ID || exam.mode !== "exam" || exam.status !== "active" || typeof exam.id !== "string") throw new Error("Active exam is unsafe or invalid.");
  assertIds(exam.questionIds, "Active exam questions", "gq-");
  if (!exam.questionIds.length) throw new Error("Active exam cannot be empty.");
  const questionsById = new Map(exam.questionIds.map((id) => [id, assertCanonicalQuestion(id, canonical)]));
  if ([...questionsById.values()].some((question) => question && !isExamEligible(question, canonical.course ?? {}))) {
    throw new Error("Active exam contains a question that is no longer Mock Exam-eligible.");
  }
  if (!isPlainObject(exam.answers)) throw new Error("Active exam answers are invalid.");
  for (const [id, answer] of Object.entries(exam.answers)) {
    if (!exam.questionIds.includes(id) || !isPlainObject(answer) || Object.keys(answer).length !== 2 || !Object.hasOwn(answer, "response") || !Object.hasOwn(answer, "answeredAt")) throw new Error("Active exam answers are unsafe.");
    if (!isAnswer(answer.response) || !Number.isFinite(answer.answeredAt) || answer.answeredAt < 0) throw new Error("Active exam answers are invalid.");
    if (questionsById.get(id) && !isValidResponse(questionsById.get(id), answer.response)) throw new Error("Active exam answers are invalid.");
  }
  if (!Number.isInteger(exam.index) || exam.index < 0 || exam.index >= exam.questionIds.length) throw new Error("Active exam position is invalid.");
  for (const [key, label] of [["flagged", "Active exam flags"], ["bookmarked", "Active exam bookmarks"]]) {
    assertIds(exam[key], label, "gq-");
    if (!exam[key].every((id) => exam.questionIds.includes(id))) throw new Error(`${label} contains an unavailable question.`);
  }
  if (!Number.isFinite(exam.startedAt) || !Number.isFinite(exam.endsAt) || exam.startedAt < 0 || exam.endsAt < exam.startedAt) throw new Error("Active exam timer is invalid.");
  if (Object.hasOwn(exam, "emptyReason") && exam.emptyReason !== null && typeof exam.emptyReason !== "string") throw new Error("Active exam empty state is invalid.");
}

function validated(state, canonical) {
  const canonicalRecords = canonicalContext(canonical);
  assertKeys(state, STATE_KEYS, "Progress state");
  if (state.version !== STATE_VERSION) throw new Error(`Unsupported progress version: ${state.version ?? "missing"}.`);
  if (state.projectId !== PROJECT_ID) throw new Error("Progress belongs to a different project.");
  assertTimestamp(state.updatedAt, "Progress state timestamp");
  assertLessons(state.lessonProgress, canonicalRecords);
  assertProgress(state.questionProgress, canonicalRecords);
  assertKeys(state.bookmarks, ["lessonIds", "questionIds"], "Bookmarks");
  assertIds(state.bookmarks.lessonIds, "Lesson bookmarks", "lesson-");
  assertQuestionIds(state.bookmarks.questionIds, "Question bookmarks");
  state.bookmarks.lessonIds.forEach((id) => assertCanonicalLesson(id, canonicalRecords));
  state.bookmarks.questionIds.forEach((id) => assertCanonicalQuestion(id, canonicalRecords));
  assertMistakes(state.mistakes, canonicalRecords);
  if (!Array.isArray(state.recentSessions)) throw new Error("Recent sessions are invalid.");
  state.recentSessions.forEach(assertSession);
  if (new Set(state.recentSessions.map((session) => session.id)).size !== state.recentSessions.length) throw new Error("Recent sessions contain duplicate IDs.");
  assertActiveExam(state.activeExam, canonicalRecords);
  return freeze(clone(state));
}

function currentTimestamp(now) {
  return typeof now === "string" ? now : new Date(typeof now === "number" ? now : Date.now()).toISOString();
}

function withUpdatedAt(state, now) {
  return { ...clone(state), updatedAt: currentTimestamp(now) };
}

export function createDefaultState(now = Date.now()) {
  return freeze({ version: STATE_VERSION, projectId: PROJECT_ID, updatedAt: currentTimestamp(now), lessonProgress: {}, questionProgress: {}, bookmarks: { lessonIds: [], questionIds: [] }, mistakes: {}, recentSessions: [], activeExam: null });
}

function defaultStorage() {
  if (!globalThis.localStorage) throw new Error("Local storage is unavailable.");
  return globalThis.localStorage;
}

export function loadState(storage = defaultStorage(), now = Date.now(), canonical) {
  const raw = storage.getItem(STORAGE_KEY);
  if (!raw) return createDefaultState(now);
  try {
    return importState(raw, canonical);
  } catch {
    storage.setItem(BACKUP_STORAGE_KEY, raw);
    return createDefaultState(now);
  }
}

export function saveState(state, storage = defaultStorage(), canonical) {
  const safe = validated(state, canonical);
  storage.setItem(STORAGE_KEY, JSON.stringify(safe));
  return safe;
}

export function exportState(state, canonical) {
  return JSON.stringify(validated(state, canonical), null, 2);
}

export function importState(raw, canonical) {
  let value;
  try {
    value = typeof raw === "string" ? JSON.parse(raw) : raw;
  } catch {
    throw new Error("The selected progress file is not valid JSON.");
  }
  return validated(value, canonical);
}

export function resetState(storage = defaultStorage(), now = Date.now()) {
  storage.removeItem(STORAGE_KEY);
  storage.removeItem(BACKUP_STORAGE_KEY);
  return createDefaultState(now);
}

export function recordAttempt(state, attempt, now = attempt?.at ?? Date.now(), canonical) {
  const canonicalRecords = canonicalContext(canonical);
  const safe = validated(state, canonical);
  if (!attempt?.questionId) throw new Error("An attempt requires a canonical question ID.");
  const question = assertCanonicalQuestion(attempt.questionId, canonicalRecords);
  if (attempt.scored !== true || attempt.finalized !== true) return validated(withUpdatedAt(safe, now), canonical);
  if (typeof attempt.correct !== "boolean" || !isAnswer(attempt.response ?? attempt.answer ?? attempt.selectedAnswer)) throw new Error("A scored attempt has an invalid answer.");
  const answer = attempt.response ?? attempt.answer ?? attempt.selectedAnswer;
  if (question && (!isScoreable(question) || !isValidResponse(question, answer))) throw new Error("A scored attempt has an invalid answer.");
  const timestamp = currentTimestamp(attempt.at ?? now);
  const previous = safe.questionProgress[attempt.questionId] ?? { attempts: 0, correctAttempts: 0, incorrectAttempts: 0, lastCorrectAt: null };
  const next = withUpdatedAt(safe, timestamp);
  next.questionProgress[attempt.questionId] = {
    attempts: previous.attempts + 1,
    correctAttempts: previous.correctAttempts + (attempt.correct ? 1 : 0),
    incorrectAttempts: previous.incorrectAttempts + (attempt.correct ? 0 : 1),
    lastAnswer: clone(answer),
    lastAttemptAt: timestamp,
    lastCorrect: attempt.correct,
    lastCorrectAt: attempt.correct ? timestamp : previous.lastCorrectAt,
  };
  if (!attempt.correct) {
    const mistake = next.mistakes[attempt.questionId] ?? { count: 0, lastAttemptAt: timestamp };
    next.mistakes[attempt.questionId] = { count: mistake.count + 1, lastAttemptAt: timestamp };
  }
  return validated(next, canonical);
}

export function toggleBookmark(state, kind, id, now = Date.now(), canonical) {
  const canonicalRecords = canonicalContext(canonical);
  const safe = validated(state, canonical);
  const field = kind === "lesson" ? "lessonIds" : kind === "question" ? "questionIds" : null;
  if (!field) throw new Error("A bookmark requires a canonical lesson or question ID.");
  if (kind === "lesson") assertCanonicalLesson(id, canonicalRecords);
  else assertCanonicalQuestion(id, canonicalRecords);
  const next = withUpdatedAt(safe, now);
  const ids = new Set(next.bookmarks[field]);
  if (ids.has(id)) ids.delete(id);
  else ids.add(id);
  next.bookmarks[field] = [...ids];
  return validated(next, canonical);
}

export function markLessonComplete(state, lessonId, status = "completed", now = Date.now(), canonicalLessonIds) {
  const canonicalRecords = canonicalContext(canonicalLessonIds);
  const safe = validated(state, canonicalLessonIds);
  assertCanonicalLesson(lessonId, canonicalRecords);
  if (!["completed", "in-progress"].includes(status)) throw new Error("Lesson status must be completed or in-progress.");
  const timestamp = currentTimestamp(now);
  const next = withUpdatedAt(safe, timestamp);
  next.lessonProgress[lessonId] = { status, lastVisitedAt: timestamp };
  return validated(next, canonicalLessonIds);
}

export function setActiveExam(state, exam, now = Date.now(), canonical) {
  const canonicalRecords = canonicalContext(canonical);
  const safe = validated(state, canonical);
  assertActiveExam(exam, canonicalRecords);
  return validated({ ...withUpdatedAt(safe, now), activeExam: clone(exam) }, canonical);
}

export function clearActiveExam(state, now = Date.now(), canonical) {
  return validated({ ...withUpdatedAt(validated(state, canonical), now), activeExam: null }, canonical);
}

export function recordSessionSummary(state, summary, now = Date.now(), canonical) {
  const safe = validated(state, canonical);
  assertSession(summary);
  const next = withUpdatedAt(safe, now);
  next.recentSessions = [clone(summary), ...next.recentSessions.filter((item) => item.id !== summary.id)].slice(0, 12);
  return validated(next, canonical);
}
