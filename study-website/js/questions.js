function normalized(value) {
  return String(value ?? "").normalize("NFKC").toLocaleLowerCase().trim().replace(/\s+/g, " ");
}

function unrestricted(value) {
  return value === undefined || value === null || value === "" || value === "all";
}

function isPlainObject(value) {
  return Boolean(value) && typeof value === "object" && !Array.isArray(value) && (Object.getPrototypeOf(value) === Object.prototype || Object.getPrototypeOf(value) === null);
}

function isNonEmptyString(value) {
  return typeof value === "string" && value.trim().length > 0;
}

function isUtcTimestamp(value) {
  if (typeof value !== "string" || !/^\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}\.\d{3}Z$/.test(value)) return false;
  const date = new Date(value);
  return !Number.isNaN(date.valueOf()) && date.toISOString() === value;
}

function hasExactKeys(value, keys) {
  return isPlainObject(value) && Object.keys(value).length === keys.length && keys.every((key) => Object.hasOwn(value, key));
}

function validSourceRefs(value) {
  return Array.isArray(value) && value.length > 0 && value.every((ref) => isPlainObject(ref) && isNonEmptyString(ref.sourceId));
}

function requiredEvidenceTargets(question) {
  if (question.type === "mcq") {
    return ["prompt", "correctAnswer", "rationale", ...question.options.map((_, index) => `options[${index}]`), ...question.distractorRationales.map((_, index) => `distractorRationales[${index}]`)];
  }
  return ["prompt", "correctAnswer", "rationale", ...(question.correctAnswer === false ? ["correctedStatement"] : [])];
}

function evidenceTargetResolves(question, target) {
  if (target === "prompt") return isNonEmptyString(question.prompt);
  if (target === "correctAnswer") return validCanonicalAnswer(question);
  if (target === "rationale") return isNonEmptyString(question.rationale);
  if (target === "correctedStatement") return question.type === "true-false" && question.correctAnswer === false && isNonEmptyString(question.correctedStatement);
  const option = /^options\[(\d+)]$/.exec(target);
  if (option) return Array.isArray(question.options) && Number(option[1]) < question.options.length && isNonEmptyString(question.options[Number(option[1])]);
  const distractor = /^distractorRationales\[(\d+)]$/.exec(target);
  return Boolean(distractor && Array.isArray(question.distractorRationales) && Number(distractor[1]) < question.distractorRationales.length && isNonEmptyString(question.distractorRationales[Number(distractor[1])]));
}

function hasRequiredEvidence(question) {
  if (!Array.isArray(question.evidenceMap) || !question.evidenceMap.length) return false;
  const required = requiredEvidenceTargets(question);
  const found = new Set();
  for (const evidence of question.evidenceMap) {
    if (!isPlainObject(evidence) || !isNonEmptyString(evidence.claimId) || !isNonEmptyString(evidence.target) || !["direct", "derived"].includes(evidence.support) || !validSourceRefs(evidence.sourceRefs) || !evidenceTargetResolves(question, evidence.target) || found.has(evidence.target)) return false;
    found.add(evidence.target);
  }
  return required.every((target) => found.has(target));
}

function validCanonicalAnswer(question) {
  if (question?.type === "mcq") {
    return Array.isArray(question.options) && question.options.length === 4 && question.options.every(isNonEmptyString) && Array.isArray(question.distractorRationales) && question.distractorRationales.length === question.options.length && question.distractorRationales.every(isNonEmptyString) && Number.isInteger(question.correctAnswer) && question.correctAnswer >= 0 && question.correctAnswer < question.options.length;
  }
  return question?.type === "true-false" && typeof question.correctAnswer === "boolean" && (question.correctAnswer ? question.correctedStatement === null : isNonEmptyString(question.correctedStatement));
}

function hasApprovedHumanReview(question) {
  const approval = question?.review?.approval;
  return question?.needsReview === false && question?.qualityState === "approved" && question?.reviewState === "approved" && hasExactKeys(question?.review, ["status", "approval"]) && question.review.status === "human-reviewed" && hasExactKeys(approval, ["reviewedRecordId", "reviewedContentVersion", "status", "decision", "reviewer", "reviewedAt", "reason", "notes"]) && approval.status === "completed" && approval.decision === "approved" && approval.reviewedRecordId === question.id && approval.reviewedContentVersion === question.contentVersion && isNonEmptyString(approval.reviewer) && isUtcTimestamp(approval.reviewedAt) && isNonEmptyString(approval.reason) && isNonEmptyString(approval.notes);
}

function hasValidatedGeneratedReview(question) {
  return question?.qualityState === "validated" && question?.reviewState === "unreviewed" && hasExactKeys(question?.review, ["status"]) && question.review.status === "validated";
}

export function isScoreable(question) {
  if (!isPlainObject(question) || question.origin !== "generated" || question.needsReview !== false || question.duplicateDisposition !== "retain" || !isNonEmptyString(question.contentVersion) || typeof question.reviewNotes !== "string" || !isNonEmptyString(question.rationale) || !validCanonicalAnswer(question) || !validSourceRefs(question.sourceRefs) || !hasRequiredEvidence(question)) return false;
  return hasValidatedGeneratedReview(question) || hasApprovedHumanReview(question);
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
  const bookmarkScope = Object.hasOwn(filters, "bookmarkedIds") || Object.hasOwn(filters, "bookmarks");
  const mistakeScope = Object.hasOwn(filters, "mistakeIds") || Object.hasOwn(filters, "mistakes");
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
    if ((bookmarkScope || filters.bookmarked === true || filters.bookmarked === "only") && !bookmarkedIds.has(question.id)) return false;
    if ((mistakeScope || filters.mistake === true || filters.mistake === "only") && !mistakeIds.has(question.id)) return false;
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
