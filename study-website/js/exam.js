import { isExamEligible, isValidResponse, scoreResponse, shuffleQuestions } from "./questions.js";

const contexts = new WeakMap();

function clone(value) {
  return structuredClone(value);
}

function freeze(value, seen = new Set()) {
  if (!value || typeof value !== "object" || seen.has(value)) return value;
  seen.add(value);
  for (const item of Object.values(value)) freeze(item, seen);
  return Object.freeze(value);
}

function explanationIndex(explanations) {
  const index = new Map();
  for (const explanation of Array.isArray(explanations) ? explanations : Object.values(explanations || {})) {
    if (explanation?.questionId) index.set(explanation.questionId, explanation);
  }
  return index;
}

function attach(exam, questions, explanations) {
  contexts.set(exam, { questions: new Map(questions.map((question) => [question.id, clone(question)])), explanations: explanationIndex(explanations) });
  return exam;
}

function bounded(value, fallback, maximum) {
  const numeric = Number(value);
  const desired = Number.isInteger(numeric) && numeric >= 0 ? numeric : fallback;
  return Math.min(desired, maximum);
}

export function createExam(questions, config = {}, now = Date.now(), random = config.random ?? Math.random) {
  const course = config.course ?? {};
  const eligible = (Array.isArray(questions) ? questions : []).filter((question) => isExamEligible(question, course));
  const ordered = config.order === "random" || config.shuffle === true ? shuffleQuestions(eligible, random) : [...eligible];
  const count = bounded(config.count, course.exam?.defaultCount ?? eligible.length, eligible.length);
  const minutes = bounded(config.minutes ?? config.durationMinutes, course.exam?.defaultMinutes ?? 30, Number.MAX_SAFE_INTEGER);
  const selected = ordered.slice(0, count);
  const exam = freeze({
    id: config.id ?? `exam-${now}`,
    projectId: config.projectId ?? course.projectId ?? course.project?.slug ?? "operating-systems-study",
    mode: "exam",
    status: selected.length ? "active" : "empty",
    questionIds: selected.map((question) => question.id),
    answers: {},
    index: 0,
    flagged: [],
    bookmarked: [],
    startedAt: now,
    endsAt: now + minutes * 60_000,
    emptyReason: selected.length ? null : "No Mock Exam-eligible questions match this selection.",
  });
  return attach(exam, selected, config.explanations);
}

export function hydrateExam(exam, questions, explanations = []) {
  const known = new Map((questions || []).map((question) => [question.id, question]));
  const selected = (exam.questionIds || []).map((id) => known.get(id)).filter(Boolean);
  return attach(freeze(clone(exam)), selected, explanations);
}

function contextFor(exam, questions, explanations) {
  if (Array.isArray(questions)) {
    const selected = new Map(questions.map((question) => [question.id, question]));
    return { questions: selected, explanations: explanationIndex(explanations) };
  }
  const context = contexts.get(exam);
  if (!context) throw new Error("Exam questions are unavailable. Hydrate the exam before answering or submitting.");
  return context;
}

function reattach(next, context) {
  return attach(next, [...context.questions.values()], [...context.explanations.values()]);
}

export function getExamRemainingSeconds(exam, now = Date.now()) {
  if (!Number.isFinite(exam?.endsAt)) return 0;
  return Math.max(0, Math.floor((exam.endsAt - now) / 1000));
}

export function isExamExpired(exam, now = Date.now()) {
  return exam?.status === "active" && now >= exam.endsAt;
}

export function goToExamQuestion(exam, index) {
  const target = Math.min(Math.max(0, Number(index) || 0), Math.max(0, exam.questionIds.length - 1));
  const next = freeze({ ...clone(exam), index: target });
  const context = contexts.get(exam);
  return context ? reattach(next, context) : next;
}

export function moveExamQuestion(exam, direction) {
  return goToExamQuestion(exam, exam.index + Number(direction || 0));
}

function toggleId(exam, key, id) {
  if (!exam.questionIds.includes(id)) return freeze(clone(exam));
  const values = new Set(exam[key]);
  if (values.has(id)) values.delete(id);
  else values.add(id);
  const next = freeze({ ...clone(exam), [key]: [...values] });
  const context = contexts.get(exam);
  return context ? reattach(next, context) : next;
}

export function toggleExamFlag(exam, questionId) {
  return toggleId(exam, "flagged", questionId);
}

export function toggleExamBookmark(exam, questionId) {
  return toggleId(exam, "bookmarked", questionId);
}

export function answerExamQuestion(exam, response, now = Date.now(), questions) {
  if (exam.status !== "active") return freeze(clone(exam));
  const context = contextFor(exam, questions);
  const questionId = exam.questionIds[exam.index];
  const question = context.questions.get(questionId);
  if (!question) throw new Error("The current exam question is unavailable.");
  if (!isValidResponse(question, response)) return reattach(freeze(clone(exam)), context);
  const next = freeze({
    ...clone(exam),
    answers: { ...clone(exam.answers), [questionId]: { response: clone(response), answeredAt: now } },
  });
  return reattach(next, context);
}

function submissionArguments(nowOrQuestions, maybeNow, maybeExplanations) {
  if (Array.isArray(nowOrQuestions)) return { questions: nowOrQuestions, now: typeof maybeNow === "number" ? maybeNow : Date.now(), explanations: maybeExplanations };
  if (nowOrQuestions && typeof nowOrQuestions === "object") return { now: nowOrQuestions.now ?? Date.now(), questions: nowOrQuestions.questions, explanations: nowOrQuestions.explanations };
  return { now: typeof nowOrQuestions === "number" ? nowOrQuestions : Date.now(), questions: undefined, explanations: undefined };
}

export function submitExam(exam, nowOrQuestions = Date.now(), maybeNow, maybeExplanations) {
  if (exam.status === "submitted") return exam;
  const { now, questions, explanations } = submissionArguments(nowOrQuestions, maybeNow, maybeExplanations);
  const context = contextFor(exam, questions, explanations);
  const reviews = exam.questionIds.map((questionId) => {
    const question = context.questions.get(questionId);
    if (!question) throw new Error(`Exam question ${questionId} is unavailable.`);
    const saved = exam.answers[questionId];
    const result = saved ? scoreResponse(question, saved.response) : { answered: false, valid: false, scored: false, correct: null, correctAnswer: question.correctAnswer };
    const explanation = context.explanations.get(questionId) ?? null;
    return {
      questionId,
      response: saved ? clone(saved.response) : null,
      answeredAt: saved?.answeredAt ?? null,
      unanswered: !result.valid,
      ...result,
      rationale: question.rationale ?? null,
      sourceRefs: clone(question.sourceRefs ?? []),
      explanation: explanation ? clone(explanation) : null,
    };
  });
  const scoreable = reviews.length;
  const correct = reviews.filter((review) => review.scored && review.correct).length;
  const incorrect = reviews.filter((review) => review.scored && !review.correct).length;
  const submittedAt = Math.max(exam.startedAt, Math.min(now, exam.endsAt));
  const result = freeze({
    ...clone(exam),
    status: "submitted",
    submittedAt,
    reviews,
    summary: {
      total: reviews.length,
      scoreable,
      correct,
      incorrect,
      unanswered: reviews.filter((review) => review.unanswered).length,
      percentage: scoreable ? Math.round((correct / scoreable) * 100) : 0,
      durationSeconds: Math.max(0, Math.floor((submittedAt - exam.startedAt) / 1000)),
    },
  });
  return result;
}

export function finalizeExpiredExam(exam, now = Date.now()) {
  return isExamExpired(exam, now) ? submitExam(exam, now) : exam;
}
