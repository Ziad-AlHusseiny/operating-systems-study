import { isScoreable, scoreResponse, shuffleQuestions } from "./questions.js";

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
  const values = Array.isArray(explanations) ? explanations : Object.values(explanations || {});
  for (const explanation of values) {
    if (explanation?.questionId) index.set(explanation.questionId, explanation);
  }
  return index;
}

function attach(session, questions, explanations) {
  contexts.set(session, { questions: new Map(questions.map((question) => [question.id, clone(question)])), explanations: explanationIndex(explanations) });
  return session;
}

function boundedCount(count, fallback, available) {
  const requested = Number.isInteger(Number(count)) && Number(count) >= 0 ? Number(count) : fallback;
  return Math.min(requested, available);
}

export function createPracticeSession(questions, config = {}, now = Date.now()) {
  const eligible = (Array.isArray(questions) ? questions : []).filter(isScoreable);
  const ordered = config.order === "random" || config.shuffle === true ? shuffleQuestions(eligible, config.random ?? Math.random) : [...eligible];
  const selected = ordered.slice(0, boundedCount(config.count, eligible.length, eligible.length));
  const session = freeze({
    id: config.id ?? `practice-${now}`,
    mode: "practice",
    status: selected.length ? "active" : "empty",
    questionIds: selected.map((question) => question.id),
    index: 0,
    answers: {},
    startedAt: now,
    feedbackVisible: false,
    emptyReason: selected.length ? null : "No eligible practice questions match this selection.",
  });
  return attach(session, selected, config.explanations);
}

export function hydratePracticeSession(session, questions, explanations = []) {
  const known = new Map((questions || []).map((question) => [question.id, question]));
  const selected = (session.questionIds || []).map((id) => known.get(id)).filter(Boolean);
  return attach(freeze(clone(session)), selected, explanations);
}

function contextFor(session) {
  const context = contexts.get(session);
  if (!context) throw new Error("Practice session questions are unavailable. Hydrate the session before answering.");
  return context;
}

export function answerPracticeQuestion(session, response, now = Date.now()) {
  if (session.status !== "active") return freeze(clone(session));
  const context = contextFor(session);
  const questionId = session.questionIds[session.index];
  const question = context.questions.get(questionId);
  if (!question) throw new Error("The current practice question is unavailable.");
  const result = scoreResponse(question, response);
  if (!result.valid) return attach(freeze({ ...clone(session), feedbackVisible: false }), [...context.questions.values()], [...context.explanations.values()]);
  const explanation = context.explanations.get(question.id) ?? null;
  const next = freeze({
    ...clone(session),
    answers: {
      ...clone(session.answers),
      [question.id]: { response: clone(response), answeredAt: now, ...result },
    },
    feedbackVisible: true,
    feedback: {
      questionId: question.id,
      ...result,
      rationale: question.rationale ?? null,
      sourceRefs: clone(question.sourceRefs ?? []),
      explanation: explanation ? clone(explanation) : null,
    },
  });
  return attach(next, [...context.questions.values()], [...context.explanations.values()]);
}

export function goToPracticeQuestion(session, index) {
  const target = Math.min(Math.max(0, Number(index) || 0), Math.max(0, session.questionIds.length - 1));
  const next = freeze({ ...clone(session), index: target, feedbackVisible: false });
  const context = contexts.get(session);
  return context ? attach(next, [...context.questions.values()], [...context.explanations.values()]) : next;
}

export function movePracticeQuestion(session, direction) {
  return goToPracticeQuestion(session, session.index + Number(direction || 0));
}
