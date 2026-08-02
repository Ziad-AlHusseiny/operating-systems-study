import { getPerformanceBreakdown, getWeakTopics } from "./statistics.js";

export function questionsForCollection(questions, collection) {
  if (!collection || collection === "all") return [...questions];
  return questions.filter((question) =>
    question.sources?.some((source) => source.collection === collection)
  );
}

export function buildRevisionSummary(questions, state) {
  const bookmarks = new Set(state.bookmarks || []);
  const mistakes = questions
    .filter(
      (question) =>
        !question.needsReview && state.progress?.[question.id]?.status === "wrong"
    )
    .sort(
      (left, right) =>
        (state.progress?.[right.id]?.incorrectAttempts || 0) -
        (state.progress?.[left.id]?.incorrectAttempts || 0)
    );
  const weakTopics = getWeakTopics(questions, state).map((item) => ({
    topic: item.name,
    answered: item.answered,
    correct: item.correct,
    wrong: item.wrong,
    accuracy: item.accuracy,
  }));
  return {
    mistakes,
    bookmarks: questions.filter((question) => bookmarks.has(question.id)),
    weakTopics,
    byTopic: getPerformanceBreakdown(questions, state, "topic"),
    bySource: getPerformanceBreakdown(questions, state, "source"),
  };
}
