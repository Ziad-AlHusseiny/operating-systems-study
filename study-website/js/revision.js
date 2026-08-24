import { isScoreable } from "./questions.js";

function clone(value) {
  return structuredClone(value);
}

function stateBookmarks(state) {
  return state?.bookmarks && !Array.isArray(state.bookmarks) ? state.bookmarks : { lessonIds: [], questionIds: [] };
}

function links(data) {
  const objectiveToLesson = { ...(data?.objectiveToLesson || {}) };
  const lessonToModule = { ...(data?.lessonToModule || {}) };
  for (const lesson of data?.lessons || []) {
    lessonToModule[lesson.id] ??= lesson.moduleId;
    for (const objectiveId of lesson.objectiveIds || []) objectiveToLesson[objectiveId] ??= lesson.id;
  }
  return { objectiveToLesson, lessonToModule };
}

function questionModule(question, dataLinks) {
  const lessonId = question.lessonId ?? dataLinks.objectiveToLesson[question.learningObjectiveId ?? question.objectiveId];
  return question.moduleId ?? dataLinks.lessonToModule[lessonId] ?? null;
}

function groupPerformance(questions, progress, keyFor, names) {
  const groups = new Map();
  for (const question of questions) {
    const key = keyFor(question);
    const entry = progress?.[question.id];
    if (!key || !entry?.attempts) continue;
    const group = groups.get(key) ?? { id: key, title: names?.[key] ?? key, answered: 0, correct: 0, incorrect: 0 };
    group.answered += entry.attempts;
    group.correct += entry.correctAttempts;
    group.incorrect += entry.incorrectAttempts;
    groups.set(key, group);
  }
  return [...groups.values()].map((group) => ({ ...group, accuracy: group.answered ? Math.round((group.correct / group.answered) * 100) : 0 }));
}

function weakAreas(groups) {
  return groups.filter((group) => group.answered > 0 && group.accuracy < 70).sort((left, right) => left.accuracy - right.accuracy || right.incorrect - left.incorrect || left.id.localeCompare(right.id));
}

export function getMistakeQuestions(questions, state = {}) {
  const progress = state.questionProgress || {};
  const mistakes = state.mistakes || {};
  return (questions || []).filter(isScoreable).map((question) => {
    const mistake = mistakes[question.id];
    if (!mistake?.count) return null;
    const entry = progress[question.id] || {};
    const masteredAfterMistake = Boolean(entry.lastCorrect && entry.lastCorrectAt && entry.lastCorrectAt >= mistake.lastAttemptAt);
    return { ...clone(question), mistakeCount: mistake.count, lastMistakeAt: mistake.lastAttemptAt, masteredAfterMistake };
  }).filter(Boolean).sort((left, right) => right.mistakeCount - left.mistakeCount || right.lastMistakeAt.localeCompare(left.lastMistakeAt) || left.id.localeCompare(right.id));
}

export function getBookmarkedQuestions(questions, state = {}) {
  const bookmarked = new Set(stateBookmarks(state).questionIds || []);
  return (questions || []).filter((question) => bookmarked.has(question.id)).map(clone);
}

export function getBookmarkedLessons(lessons, state = {}) {
  const bookmarked = new Set(stateBookmarks(state).lessonIds || []);
  return (lessons || []).filter((lesson) => bookmarked.has(lesson.id)).map(clone);
}

export function getRevisionSummary(data, state = {}) {
  const lessons = data?.lessons || [];
  const questions = (data?.questions || []).filter(isScoreable);
  const modules = data?.modules || [];
  const progress = state.questionProgress || {};
  const dataLinks = links(data);
  const moduleNames = Object.fromEntries(modules.map((module) => [module.id, module.title]));
  const completed = lessons.filter((lesson) => state.lessonProgress?.[lesson.id]?.status === "completed").length;
  const attempts = questions.reduce((total, question) => {
    const entry = progress[question.id];
    if (!entry) return total;
    total.answered += entry.attempts || 0;
    total.correct += entry.correctAttempts || 0;
    total.incorrect += entry.incorrectAttempts || 0;
    return total;
  }, { answered: 0, correct: 0, incorrect: 0 });
  attempts.accuracy = attempts.answered ? Math.round((attempts.correct / attempts.answered) * 100) : 0;
  const topicPerformance = groupPerformance(questions, progress, (question) => question.topic, null);
  const modulePerformance = groupPerformance(questions, progress, (question) => questionModule(question, dataLinks), moduleNames);
  const mistakes = getMistakeQuestions(questions, state);
  const bookmarkedQuestions = getBookmarkedQuestions(questions, state);
  const bookmarkedLessons = getBookmarkedLessons(lessons, state);
  return {
    lessons: { completed, total: lessons.length },
    attempts,
    weakModules: weakAreas(modulePerformance),
    weakTopics: weakAreas(topicPerformance),
    modulePerformance,
    topicPerformance,
    mistakeCount: mistakes.reduce((total, question) => total + question.mistakeCount, 0),
    mistakeQuestionCount: mistakes.length,
    bookmarks: { lessons: bookmarkedLessons.length, questions: bookmarkedQuestions.length },
    recentSessions: clone(state.recentSessions || []),
    revisionCards: [
      { id: "lessons", label: "Lessons completed", value: `${completed}/${lessons.length}` },
      { id: "accuracy", label: "Overall accuracy", value: attempts.accuracy },
      { id: "mistakes", label: "Historical mistakes", value: mistakes.length },
      { id: "bookmarks", label: "Bookmarks", value: bookmarkedLessons.length + bookmarkedQuestions.length },
    ],
  };
}
