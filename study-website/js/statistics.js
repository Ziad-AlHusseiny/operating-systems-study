function percentage(numerator, denominator) {
  return denominator ? Math.round((numerator / denominator) * 100) : 0;
}

export function getDashboardStats(questions, state) {
  let correct = 0;
  let wrong = 0;
  for (const question of questions) {
    const status = state.progress?.[question.id]?.status;
    if (status === "correct") correct += 1;
    if (status === "wrong") wrong += 1;
  }
  const answered = correct + wrong;
  return {
    total: questions.length,
    answered,
    correct,
    wrong,
    unanswered: Math.max(0, questions.length - answered),
    accuracy: percentage(correct, answered),
    completion: percentage(answered, questions.length),
  };
}

function dimensionValues(question, dimension) {
  if (dimension === "source") {
    return [
      ...new Set(
        (question.sources || []).map((source) => source.collection)
      ),
    ];
  }
  const value = question[dimension];
  return value ? [value] : ["Uncategorized"];
}

export function getPerformanceBreakdown(questions, state, dimension = "topic") {
  const groups = new Map();
  for (const question of questions) {
    for (const name of dimensionValues(question, dimension)) {
      if (!groups.has(name)) {
        groups.set(name, { name, total: 0, answered: 0, correct: 0, wrong: 0 });
      }
      const group = groups.get(name);
      group.total += 1;
      const status = state.progress?.[question.id]?.status;
      if (status === "correct") {
        group.answered += 1;
        group.correct += 1;
      } else if (status === "wrong") {
        group.answered += 1;
        group.wrong += 1;
      }
    }
  }
  return [...groups.values()].map((group) => ({
    ...group,
    accuracy: percentage(group.correct, group.answered),
  }));
}

export function getWeakTopics(questions, state, minimumAnswered = 1) {
  return getPerformanceBreakdown(questions, state, "topic")
    .filter((topic) => topic.answered >= minimumAnswered)
    .sort((left, right) => left.accuracy - right.accuracy || right.answered - left.answered);
}

export function getSessionStats(questionIds, answers, durationSeconds = 0) {
  const total = questionIds.length;
  const values = Object.values(answers || {});
  const correct = values.filter((answer) => answer.correct === true).length;
  const wrong = values.filter((answer) => answer.correct === false).length;
  const skipped = Math.max(0, total - correct - wrong);
  return {
    total,
    correct,
    wrong,
    skipped,
    answered: correct + wrong,
    accuracy: percentage(correct, correct + wrong),
    durationSeconds: Math.max(0, Math.round(durationSeconds)),
  };
}
