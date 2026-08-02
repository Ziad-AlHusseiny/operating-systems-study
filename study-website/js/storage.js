import { getSessionStats } from "./statistics.js";

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

function reviewAnswerForOverride(question, override) {
  const choiceOrder = override.choiceOrder;
  if (!Array.isArray(choiceOrder)) return question.correctAnswer;
  if (question.type === "mcq" && Number.isInteger(question.correctAnswer)) {
    return choiceOrder.indexOf(question.correctAnswer);
  }
  if (question.type === "multi-select" && Array.isArray(question.correctAnswer)) {
    return question.correctAnswer
      .map((index) => choiceOrder.indexOf(index))
      .sort((left, right) => left - right);
  }
  return question.correctAnswer;
}

function sanitizeSession(session, reviewQuestions) {
  if (!isPlainObject(session)) return session;
  const answers = isPlainObject(session.answers) ? { ...session.answers } : {};
  for (const [questionId, answer] of Object.entries(answers)) {
    if (!reviewQuestions.has(questionId)) continue;
    const savedAnswer = isPlainObject(answer) ? answer : { response: answer };
    answers[questionId] = {
      ...savedAnswer,
      correct: null,
      earned: 0,
      possible: 0,
    };
  }

  let questionOverrides = session.questionOverrides;
  if (isPlainObject(questionOverrides)) {
    questionOverrides = { ...questionOverrides };
    for (const [questionId, override] of Object.entries(questionOverrides)) {
      const question = reviewQuestions.get(questionId);
      if (!question || !isPlainObject(override)) continue;
      questionOverrides[questionId] = {
        ...override,
        correctAnswer: reviewAnswerForOverride(question, override),
        needsReview: true,
        reviewNotes: question.reviewNotes || "This answer key requires review.",
      };
    }
  }

  const sanitized = { ...session, answers };
  if (questionOverrides !== undefined) sanitized.questionOverrides = questionOverrides;
  if (isPlainObject(session.stats) || session.finishedAt != null) {
    sanitized.stats = getSessionStats(
      Array.isArray(session.questionIds) ? session.questionIds : [],
      answers,
      session.stats?.durationSeconds || 0
    );
  }
  return sanitized;
}

export function normalizeStateForQuestions(state, questions) {
  const current = normalizeState(validateState(state));
  const reviewQuestions = new Map(
    (questions || [])
      .filter((question) => question?.needsReview)
      .map((question) => [question.id, question])
  );
  if (!reviewQuestions.size) return current;

  const progress = { ...current.progress };
  for (const questionId of reviewQuestions.keys()) delete progress[questionId];

  const sanitizeHistoryEntry = (entry) =>
    isPlainObject(entry) && reviewQuestions.has(entry.questionId)
      ? { ...entry, correct: null }
      : entry;
  const activeExamHasReview = current.activeExam?.questionIds?.some((questionId) =>
    reviewQuestions.has(questionId)
  );

  return {
    ...current,
    progress,
    history: current.history.map(sanitizeHistoryEntry),
    sessions: current.sessions.map((session) => sanitizeSession(session, reviewQuestions)),
    exams: current.exams.map((session) => sanitizeSession(session, reviewQuestions)),
    activePractice: sanitizeSession(current.activePractice, reviewQuestions),
    activeExam: activeExamHasReview
      ? null
      : sanitizeSession(current.activeExam, reviewQuestions),
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
