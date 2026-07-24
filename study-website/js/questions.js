export async function loadQuestionBank(url = "./data/questions.json") {
  const response = await fetch(url);
  if (!response.ok) {
    throw new Error(`Could not load the question bank (${response.status}).`);
  }
  const data = await response.json();
  if (!data || !Array.isArray(data.questions)) {
    throw new Error("The question bank has an invalid format.");
  }
  return data;
}

export function filterQuestions(questions, filters = {}) {
  const search = String(filters.search || "").trim().toLowerCase();
  const progress = filters.progress || {};
  const bookmarks = new Set(filters.bookmarks || []);

  return questions.filter((question) => {
    if (
      filters.source &&
      filters.source !== "all" &&
      !question.sources?.some((source) => source.collection === filters.source)
    ) {
      return false;
    }
    if (filters.type && filters.type !== "all" && question.type !== filters.type) {
      return false;
    }
    if (filters.topic && filters.topic !== "all" && question.topic !== filters.topic) {
      return false;
    }
    if (filters.needsReview === true && !question.needsReview) {
      return false;
    }
    if (filters.needsReview === false && question.needsReview) {
      return false;
    }
    if (filters.bookmarked === true && !bookmarks.has(question.id)) {
      return false;
    }

    const status = progress[question.id]?.status || "unanswered";
    if (filters.status && filters.status !== "all" && status !== filters.status) {
      return false;
    }

    if (search) {
      const haystack = [
        question.prompt,
        question.topic,
        ...(question.options || []),
        ...(question.statements || []),
      ]
        .join(" ")
        .toLowerCase();
      if (!haystack.includes(search)) return false;
    }
    return true;
  });
}

export function shuffleQuestions(questions, random = Math.random) {
  const copy = [...questions];
  for (let index = copy.length - 1; index > 0; index -= 1) {
    const swapIndex = Math.floor(random() * (index + 1));
    [copy[index], copy[swapIndex]] = [copy[swapIndex], copy[index]];
  }
  return copy;
}

export function shuffleChoices(question, random = Math.random) {
  if (!["mcq", "multi-select"].includes(question.type) || !question.options?.length) {
    return {
      ...question,
      options: [...(question.options || [])],
    };
  }

  const indexed = question.options.map((value, originalIndex) => ({
    value,
    originalIndex,
  }));
  for (let index = indexed.length - 1; index > 0; index -= 1) {
    const swapIndex = Math.floor(random() * (index + 1));
    [indexed[index], indexed[swapIndex]] = [indexed[swapIndex], indexed[index]];
  }

  const newIndexByOriginal = new Map(
    indexed.map((item, newIndex) => [item.originalIndex, newIndex])
  );
  const correctAnswer =
    question.type === "mcq"
      ? newIndexByOriginal.get(question.correctAnswer)
      : question.correctAnswer
          .map((index) => newIndexByOriginal.get(index))
          .sort((left, right) => left - right);

  return {
    ...question,
    options: indexed.map((item) => item.value),
    correctAnswer,
    choiceOrder: indexed.map((item) => item.originalIndex),
  };
}
