import { scoreResponse } from "./question-renderer.js";
import { shuffleQuestions } from "./questions.js";
import { getSessionStats } from "./statistics.js";

export function createSession(questions, config = {}, random = Math.random, now = Date.now()) {
  const eligible = questions.filter((question) => {
    if (config.topic && config.topic !== "all" && question.topic !== config.topic) return false;
    if (
      config.source &&
      config.source !== "all" &&
      !question.sources?.some((source) => source.collection === config.source)
    ) {
      return false;
    }
    if (config.excludeReview && question.needsReview) return false;
    return true;
  });
  const ordered = config.shuffle === false ? [...eligible] : shuffleQuestions(eligible, random);
  const requested = Math.max(1, Number(config.count) || 10);
  const selected = ordered.slice(0, Math.min(requested, ordered.length));
  return {
    id: `${config.mode || "practice"}-${now}`,
    mode: config.mode || "practice",
    questionIds: selected.map((question) => question.id),
    index: 0,
    answers: {},
    flagged: [],
    startedAt: now,
    durationMinutes: Math.max(0, Number(config.durationMinutes) || 0),
    finishedAt: null,
    config: { ...config },
  };
}

export function answerSessionQuestion(session, question, response, now = Date.now()) {
  const result = scoreResponse(question, response);
  return {
    ...session,
    answers: {
      ...session.answers,
      [question.id]: {
        response,
        ...result,
        answeredAt: now,
      },
    },
  };
}

export function moveSession(session, direction) {
  const target = Math.min(
    Math.max(0, session.index + Number(direction || 0)),
    Math.max(0, session.questionIds.length - 1)
  );
  return { ...session, index: target };
}

export function goToSessionQuestion(session, index) {
  const target = Math.min(Math.max(0, Number(index) || 0), Math.max(0, session.questionIds.length - 1));
  return { ...session, index: target };
}

export function toggleSessionFlag(session, questionId) {
  const flags = new Set(session.flagged || []);
  if (flags.has(questionId)) flags.delete(questionId);
  else flags.add(questionId);
  return { ...session, flagged: [...flags] };
}

export function getRemainingSeconds(session, now = Date.now()) {
  if (!session.durationMinutes) return null;
  const elapsed = Math.floor((now - session.startedAt) / 1000);
  return Math.max(0, session.durationMinutes * 60 - elapsed);
}

export function finishSession(session, now = Date.now()) {
  return {
    ...session,
    finishedAt: now,
    stats: getSessionStats(
      session.questionIds,
      session.answers,
      Math.max(0, (now - session.startedAt) / 1000)
    ),
  };
}
