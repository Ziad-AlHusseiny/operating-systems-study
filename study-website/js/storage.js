export const STORAGE_KEY = "its-study-progress-v1";
export const STATE_VERSION = 1;

export function createDefaultState() {
  return {
    version: STATE_VERSION,
    progress: {},
    bookmarks: [],
    history: [],
    sessions: [],
    exams: [],
    theme: "light",
    lastQuestionId: null,
    activePractice: null,
    activeExam: null,
  };
}

function isPlainObject(value) {
  return Boolean(value) && typeof value === "object" && !Array.isArray(value);
}

function validateState(value) {
  if (!isPlainObject(value)) throw new Error("Progress data must be an object.");
  if (value.version !== STATE_VERSION) {
    throw new Error(`Unsupported progress version: ${value.version ?? "missing"}.`);
  }
  if (!isPlainObject(value.progress)) throw new Error("Progress entries are invalid.");
  if (!Array.isArray(value.bookmarks)) throw new Error("Bookmarks must be an array.");
  if (!value.bookmarks.every((id) => typeof id === "string")) {
    throw new Error("Bookmarks contain an invalid question ID.");
  }
  for (const field of ["history", "sessions", "exams"]) {
    if (!Array.isArray(value[field])) throw new Error(`${field} must be an array.`);
  }
  return value;
}

function normalizeState(value) {
  const defaults = createDefaultState();
  return {
    ...defaults,
    ...value,
    progress: { ...value.progress },
    bookmarks: [...value.bookmarks],
    history: [...value.history],
    sessions: [...value.sessions],
    exams: [...value.exams],
  };
}

export function loadState(storage = localStorage) {
  const raw = storage.getItem(STORAGE_KEY);
  if (!raw) return createDefaultState();
  try {
    return importState(raw);
  } catch {
    return createDefaultState();
  }
}

export function saveState(state, storage = localStorage) {
  const valid = normalizeState(validateState(state));
  storage.setItem(STORAGE_KEY, JSON.stringify(valid));
  return valid;
}

export function recordAttempt(state, attempt) {
  if (!attempt?.questionId || typeof attempt.questionId !== "string") {
    throw new Error("An attempt requires a question ID.");
  }
  const previous = state.progress[attempt.questionId] || {
    attempts: 0,
    incorrectAttempts: 0,
  };
  const progressEntry = {
    ...previous,
    status: attempt.correct ? "correct" : "wrong",
    lastAnswer: attempt.selectedAnswer,
    lastCorrect: Boolean(attempt.correct),
    attempts: (previous.attempts || 0) + 1,
    incorrectAttempts:
      (previous.incorrectAttempts || 0) + (attempt.correct ? 0 : 1),
    lastAnsweredAt: attempt.at || new Date().toISOString(),
  };
  return {
    ...state,
    progress: {
      ...state.progress,
      [attempt.questionId]: progressEntry,
    },
    history: [
      ...state.history,
      {
        questionId: attempt.questionId,
        selectedAnswer: attempt.selectedAnswer,
        correct: Boolean(attempt.correct),
        at: progressEntry.lastAnsweredAt,
        mode: attempt.mode || "practice",
      },
    ],
  };
}

export function toggleBookmark(state, questionId) {
  const bookmarks = new Set(state.bookmarks);
  if (bookmarks.has(questionId)) bookmarks.delete(questionId);
  else bookmarks.add(questionId);
  return {
    ...state,
    bookmarks: [...bookmarks],
  };
}

export function exportState(state) {
  return JSON.stringify(normalizeState(validateState(state)), null, 2);
}

export function importState(json) {
  let parsed;
  try {
    parsed = typeof json === "string" ? JSON.parse(json) : json;
  } catch {
    throw new Error("The selected file is not valid JSON.");
  }
  return normalizeState(validateState(parsed));
}

export function resetState(storage = localStorage) {
  storage.removeItem(STORAGE_KEY);
  return createDefaultState();
}
