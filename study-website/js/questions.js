function normalized(value) {
  return String(value ?? "").normalize("NFKC").toLocaleLowerCase().trim().replace(/\s+/g, " ");
}

function unrestricted(value) {
  return value === undefined || value === null || value === "" || value === "all";
}

function validCanonicalAnswer(question) {
  if (question?.type === "mcq") {
    return Array.isArray(question.options) && Number.isInteger(question.correctAnswer) && question.correctAnswer >= 0 && question.correctAnswer < question.options.length;
  }
  return question?.type === "true-false" && typeof question.correctAnswer === "boolean";
}

function hasApprovedHumanReview(question) {
  const approval = question?.review?.approval;
  return question?.review?.status === "human-reviewed" || (
    approval?.status === "completed" && approval?.decision === "approved" && approval?.reviewedRecordId === question.id &&
    (approval.reviewedContentVersion === undefined || approval.reviewedContentVersion === question.contentVersion)
  );
}

export function isScoreable(question) {
  if (!question || question.origin !== "generated" || question.needsReview === true) return false;
  if (!validCanonicalAnswer(question) || !Array.isArray(question.sourceRefs) || !question.sourceRefs.length) return false;
  if (question.duplicateDisposition && question.duplicateDisposition !== "retain") return false;
  if (question.qualityState && !["validated", "approved"].includes(question.qualityState)) return false;
  if (question.reviewState && ["needs-review", "rejected"].includes(question.reviewState)) return false;
  return ["validated", "human-reviewed", "approved"].includes(question.review?.status) || hasApprovedHumanReview(question);
}

export function isExamEligible(question, course = {}) {
  return isScoreable(question) && (!course?.contentPolicy?.generatedQuestionsRequireHumanReviewForExam || hasApprovedHumanReview(question));
}

export function isValidResponse(question, response) {
  if (question?.type === "mcq") return Number.isInteger(response) && response >= 0 && response < (question.options?.length || 0);
  return question?.type === "true-false" && typeof response === "boolean";
}

export function scoreResponse(question, response) {
  const valid = isValidResponse(question, response);
  const scored = valid && isScoreable(question);
  return { answered: valid, valid, scored, correct: scored ? response === question.correctAnswer : null, correctAnswer: validCanonicalAnswer(question) ? question.correctAnswer : null };
}

function setFrom(value) {
  return new Set(Array.isArray(value) ? value : value instanceof Set ? value : []);
}

function questionLessonId(question, indexes) {
  return question.lessonId ?? indexes?.objectiveToLesson?.[question.learningObjectiveId ?? question.objectiveId];
}

function questionModuleId(question, indexes) {
  return question.moduleId ?? indexes?.lessonToModule?.[questionLessonId(question, indexes)];
}

function matchesValue(value, filter) {
  return unrestricted(filter) || value === filter;
}

export function filterQuestions(questions, filters = {}, indexes = filters.indexes ?? {}) {
  const bookmarkedIds = setFrom(filters.bookmarkedIds ?? filters.bookmarks);
  const mistakeIds = setFrom(filters.mistakeIds ?? filters.mistakes);
  const search = normalized(filters.search);
  const result = (Array.isArray(questions) ? questions : []).filter((question) => {
    const objectiveId = question.learningObjectiveId ?? question.objectiveId;
    if (!matchesValue(questionModuleId(question, indexes), filters.moduleId ?? filters.module)) return false;
    if (!matchesValue(questionLessonId(question, indexes), filters.lessonId ?? filters.lesson)) return false;
    if (!matchesValue(objectiveId, filters.objectiveId ?? filters.objective)) return false;
    if (!matchesValue(question.topic, filters.topic)) return false;
    if (!matchesValue(question.type, filters.type)) return false;
    if (!matchesValue(question.difficulty, filters.difficulty)) return false;
    if (!matchesValue(question.bloomLevel, filters.bloomLevel ?? filters.bloom)) return false;
    if (!matchesValue(question.origin, filters.origin)) return false;
    const reviewFilter = filters.review ?? filters.reviewStatus ?? filters.needsReview;
    if (!unrestricted(reviewFilter)) {
      const needsReview = question.needsReview || ["needs-review", "rejected"].includes(question.review?.status);
      if ((reviewFilter === true || reviewFilter === "needs-review") && !needsReview) return false;
      if ((reviewFilter === false || reviewFilter === "reviewed") && needsReview) return false;
      if (reviewFilter === "validated" && question.review?.status !== "validated") return false;
      if (![true, false, "needs-review", "reviewed", "validated"].includes(reviewFilter) && question.review?.status !== reviewFilter) return false;
    }
    const eligibility = filters.eligibility ?? (filters.status === "eligible" || filters.status === "ineligible" ? filters.status : undefined);
    if (eligibility === "eligible" && !isScoreable(question)) return false;
    if (eligibility === "ineligible" && isScoreable(question)) return false;
    if ((filters.bookmarked === true || filters.bookmarked === "only") && !bookmarkedIds.has(question.id)) return false;
    if ((filters.mistake === true || filters.mistake === "only") && !mistakeIds.has(question.id)) return false;
    if (search && !normalized([question.prompt, question.topic, ...(question.options || []), question.rationale].join(" ")).includes(search)) return false;
    return true;
  });
  const order = typeof filters.order === "function" ? filters.order : typeof filters.orderBy === "function" ? filters.orderBy : null;
  if (!order) return result;
  const ordered = order([...result]);
  if (!Array.isArray(ordered)) throw new Error("A question ordering operation must return an array.");
  return ordered;
}

export function shuffleQuestions(questions, random = Math.random) {
  const ordered = [...questions];
  for (let index = ordered.length - 1; index > 0; index -= 1) {
    const swap = Math.floor(random() * (index + 1));
    [ordered[index], ordered[swap]] = [ordered[swap], ordered[index]];
  }
  return ordered;
}
