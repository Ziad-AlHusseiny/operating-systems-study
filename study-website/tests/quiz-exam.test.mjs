import assert from "node:assert/strict";
import test from "node:test";
import { answerPracticeQuestion, createPracticeSession } from "../js/quiz.js";
import { answerExamQuestion, createExam, finalizeExpiredExam, getExamRemainingSeconds, goToExamQuestion, submitExam, toggleExamBookmark, toggleExamFlag } from "../js/exam.js";

function question(id, correctAnswer = 1, overrides = {}) {
  return {
    id, origin: "generated", type: typeof correctAnswer === "boolean" ? "true-false" : "mcq", prompt: `Prompt ${id}`,
    options: typeof correctAnswer === "boolean" ? undefined : ["A", "B", "C", "D"], correctAnswer, topic: "Memory", learningObjectiveId: "objective-memory",
    needsReview: false, review: { status: "validated" }, qualityState: "validated", reviewState: "unreviewed", duplicateDisposition: "retain",
    sourceRefs: [{ sourceId: "os-lec-01" }], rationale: `Rationale ${id}`, ...overrides,
  };
}
const explanations = [{ id: "explanation-one", questionId: "gq-one", translation: "\u062a\u0631\u062c\u0645\u0629 \u0639\u0631\u0628\u064a\u0629", explanation: ["\u0634\u0631\u062d \u0648\u0627\u062d\u062f", "\u0634\u0631\u062d \u0627\u062b\u0646\u0627\u0646"], note: "\u0645\u0644\u0627\u062d\u0638\u0629" }];

test("practice selects only eligible questions with bounded injected shuffle and no pre-answer leak", () => {
  const one = question("gq-one", 1, { generatedExplanationId: "explanation-one" });
  const two = question("gq-two", 2);
  const three = question("gq-three", 0);
  const review = question("gq-review", 1, { needsReview: true });
  const session = createPracticeSession([one, two, three, review], { count: 20, order: "random", random: () => 0, explanations }, 100);
  assert.deepEqual(session.questionIds, ["gq-two", "gq-three", "gq-one"]);
  assert.equal(session.status, "active");
  assert.equal(session.feedbackVisible, false);
  assert.equal(JSON.stringify(session).includes("correctAnswer"), false);
  assert.equal(JSON.stringify(session).includes("Rationale"), false);
  assert.equal(JSON.stringify(session).includes("\u062a\u0631\u062c\u0645\u0629 \u0639\u0631\u0628\u064a\u0629"), false);
  assert.equal(Object.isFrozen(session), true);
  assert.equal(createPracticeSession([review], { count: 1 }).status, "empty");
});

test("practice exposes correctness, rationale, sources, and Arabic guidance only after submission", () => {
  const item = question("gq-one", 1, { generatedExplanationId: "explanation-one" });
  const session = createPracticeSession([item], { count: 1, order: "original", explanations }, 100);
  const answered = answerPracticeQuestion(session, 1, 125);
  assert.equal(answered.feedbackVisible, true);
  assert.equal(answered.answers["gq-one"].correct, true);
  assert.equal(answered.feedback.rationale, "Rationale gq-one");
  assert.deepEqual(answered.feedback.sourceRefs, [{ sourceId: "os-lec-01" }]);
  assert.equal(answered.feedback.explanation.translation, "\u062a\u0631\u062c\u0645\u0629 \u0639\u0631\u0628\u064a\u0629");
  assert.equal(session.answers["gq-one"], undefined);
});

test("mock exams apply policy gating, absolute timers, navigation, flags, bookmarks, and no active-answer leak", () => {
  const validated = question("gq-validated", 1);
  const human = question("gq-human", 0, { review: { status: "human-reviewed", approval: { status: "completed", decision: "approved", reviewedRecordId: "gq-human" } } });
  const review = question("gq-review", 1, { needsReview: true });
  const strictCourse = { contentPolicy: { generatedQuestionsRequireHumanReviewForExam: true }, exam: { defaultCount: 10, defaultMinutes: 2 } };
  const strict = createExam([validated, human, review], { course: strictCourse }, 1_000);
  assert.deepEqual(strict.questionIds, ["gq-human"]);
  assert.equal(strict.endsAt, 121_000);
  assert.equal(getExamRemainingSeconds(strict, 1_500), 119);
  assert.equal(JSON.stringify(strict).includes("correctAnswer"), false);
  assert.equal(JSON.stringify(strict).includes("Rationale"), false);
  const exam = createExam([validated, review], { count: 1, minutes: 1 }, 1_000);
  const moved = goToExamQuestion(exam, 99);
  const flagged = toggleExamFlag(moved, "gq-validated");
  const bookmarked = toggleExamBookmark(flagged, "gq-validated");
  const invalid = answerExamQuestion(bookmarked, "1", 1_100);
  const answered = answerExamQuestion(invalid, 1, 1_200);
  assert.equal(invalid.answers["gq-validated"], undefined);
  assert.deepEqual(answered.answers["gq-validated"], { response: 1, answeredAt: 1_200 });
  assert.equal(answered.answers["gq-validated"].correct, undefined);
  assert.deepEqual(answered.flagged, ["gq-validated"]);
  assert.deepEqual(answered.bookmarked, ["gq-validated"]);
});

test("mock exam submission and expiry score only after finalization, include unanswered records, and are idempotent", () => {
  const one = question("gq-one", 1, { generatedExplanationId: "explanation-one" });
  const two = question("gq-two", false);
  const exam = createExam([one, two], { count: 2, minutes: 1, explanations }, 1_000);
  const answered = answerExamQuestion(exam, 1, 1_500);
  const result = submitExam(answered, 2_000);
  assert.equal(result.status, "submitted");
  assert.deepEqual(result.summary, { total: 2, scoreable: 2, correct: 1, incorrect: 0, unanswered: 1, percentage: 50, durationSeconds: 1 });
  assert.equal(result.reviews[0].rationale, "Rationale gq-one");
  assert.equal(result.reviews[0].explanation.translation, "\u062a\u0631\u062c\u0645\u0629 \u0639\u0631\u0628\u064a\u0629");
  assert.equal(result.reviews[1].unanswered, true);
  assert.deepEqual(submitExam(result, 9_999), result);
  const expired = createExam([one], { count: 1, minutes: 1 }, 1_000);
  const expiredResult = finalizeExpiredExam(expired, 62_000);
  assert.equal(expiredResult.status, "submitted");
  assert.equal(expiredResult.summary.durationSeconds, 60);
});
