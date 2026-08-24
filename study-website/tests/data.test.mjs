import assert from "node:assert/strict";
import test from "node:test";

import { filterLessons, loadCourseData } from "../js/data.js";
import { filterQuestions, scoreResponse } from "../js/questions.js";

const projectId = "operating-systems-study";
const clone = (value) => structuredClone(value);

function payloads() {
  return {
    "course.json": { projectId, project: { slug: projectId }, contentPolicy: { generatedQuestionsRequireHumanReviewForExam: false }, exam: { defaultCount: 2, defaultMinutes: 5 }, modules: [{ id: "module-memory", title: "Memory", order: 1 }], objectives: [{ id: "objective-paging", moduleId: "module-memory", text: "Page memory" }] },
    "lessons.json": { projectId, lessons: [{ id: "lesson-paging", moduleId: "module-memory", objectiveIds: ["objective-paging"], title: "Caf\u00e9 paging", materialSections: [{ sourceRefs: [{ sourceId: "os-lec-01" }] }] }] },
    "questions.json": { projectId, questions: [{ id: "gq-paging-1", origin: "generated", type: "mcq", prompt: "Which paging fact is true?", options: ["A", "B", "C", "D"], correctAnswer: 1, topic: "PAGING", learningObjectiveId: "objective-paging", needsReview: false, review: { status: "validated" }, qualityState: "validated", reviewState: "unreviewed", duplicateDisposition: "retain", sourceRefs: [{ sourceId: "os-lec-01" }], rationale: "Paging uses fixed-size pages.", difficulty: "easy", bloomLevel: "remember", generatedExplanationId: "explanation-paging-1" }] },
    "explanations-ar.json": { projectId, explanations: [{ id: "explanation-paging-1", questionId: "gq-paging-1", translation: "\u0645\u0627 \u0647\u064a \u0627\u0644\u0635\u0641\u062d\u0627\u062a\u061f", explanation: ["\u0634\u0631\u062d \u0623\u0648\u0644", "\u0634\u0631\u062d \u062b\u0627\u0646"], note: "\u0630\u0627\u0643\u0631 \u0627\u0644\u0635\u0641\u062d\u0627\u062a" }] },
  };
}

function response(body, { ok = true, status = 200 } = {}) { return { ok, status, json: async () => clone(body) }; }

test("loads all four payloads in parallel, builds links, and isolates returned data", async () => {
  const fixture = payloads();
  const calls = [];
  const data = await loadCourseData({ baseUrl: "/os-data/", fetchImpl: async (url) => { calls.push(url); return response(fixture[url.replace("/os-data/", "")]); } });
  assert.deepEqual(calls.sort(), ["/os-data/course.json", "/os-data/explanations-ar.json", "/os-data/lessons.json", "/os-data/questions.json"]);
  assert.equal(data.moduleById["module-memory"].title, "Memory");
  assert.equal(data.objectiveToLesson["objective-paging"], "lesson-paging");
  assert.equal(data.lessonToModule["lesson-paging"], "module-memory");
  assert.equal(data.questionById["gq-paging-1"].id, "gq-paging-1");
  assert.equal(data.explanationByQuestionId["gq-paging-1"].id, "explanation-paging-1");
  assert.throws(() => { data.questions[0].topic = "changed"; }, TypeError);
  const next = await loadCourseData({ fetchImpl: async (url) => response(fixture[url.replace("./data/", "")]) });
  assert.equal(next.questions[0].topic, "PAGING");
});

test("rejects failed responses, malformed roots, and mismatched or broken links", async () => {
  await assert.rejects(loadCourseData({ fetchImpl: async () => response({}, { ok: false, status: 503 }) }), /503/);
  const malformed = payloads(); malformed["questions.json"].questions = {};
  await assert.rejects(loadCourseData({ fetchImpl: async (url) => response(malformed[url.replace("./data/", "")]) }), /questions/i);
  const mismatch = payloads(); mismatch["lessons.json"].projectId = "another-project";
  await assert.rejects(loadCourseData({ fetchImpl: async (url) => response(mismatch[url.replace("./data/", "")]) }), /project/i);
  const broken = payloads(); broken["questions.json"].questions[0].learningObjectiveId = "objective-missing";
  await assert.rejects(loadCourseData({ fetchImpl: async (url) => response(broken[url.replace("./data/", "")]) }), /objective/i);
});

test("filters lessons by module, source, normalized search, and external completion state", () => {
  const lessons = [
    { id: "lesson-one", moduleId: "module-a", title: "Caf\u00e9 Scheduling", materialSections: [{ sourceRefs: [{ sourceId: "os-lec-01" }] }] },
    { id: "lesson-two", moduleId: "module-b", title: "Memory Management", materialSections: [{ sourceRefs: [{ sourceId: "os-lec-02" }] }] },
  ];
  const progress = { "lesson-one": { status: "completed" }, "lesson-two": { status: "in-progress" } };
  assert.deepEqual(filterLessons(lessons, { moduleId: "module-a" }).map((item) => item.id), ["lesson-one"]);
  assert.deepEqual(filterLessons(lessons, { sourceId: "os-lec-02" }).map((item) => item.id), ["lesson-two"]);
  assert.deepEqual(filterLessons(lessons, { search: "CAFE\u0301" }).map((item) => item.id), ["lesson-one"]);
  assert.deepEqual(filterLessons(lessons, { completion: "in-progress", lessonProgress: progress }).map((item) => item.id), ["lesson-two"]);
  assert.deepEqual(filterLessons(lessons, { moduleId: "all", search: "" }).map((item) => item.id), ["lesson-one", "lesson-two"]);
});

test("filters questions with AND semantics, state IDs, normalized search, stable order, and injected ordering", () => {
  const questions = [
    { id: "gq-one", origin: "generated", type: "mcq", topic: "PAGING", prompt: "Caf\u00e9 page table", options: ["a", "b", "c", "d"], correctAnswer: 0, learningObjectiveId: "objective-a", difficulty: "easy", bloomLevel: "remember", needsReview: false, review: { status: "validated" }, qualityState: "validated", reviewState: "unreviewed", duplicateDisposition: "retain", sourceRefs: [{ sourceId: "os-lec-01" }] },
    { id: "gq-two", origin: "generated", type: "true-false", topic: "Scheduling", prompt: "Round robin uses a quantum.", correctAnswer: true, learningObjectiveId: "objective-b", difficulty: "hard", bloomLevel: "analyze", needsReview: true, review: { status: "needs-review" }, qualityState: "needs-review", reviewState: "needs-review", duplicateDisposition: "needs-review", sourceRefs: [{ sourceId: "os-lec-02" }] },
  ];
  const indexes = { objectiveToLesson: { "objective-a": "lesson-a", "objective-b": "lesson-b" }, lessonToModule: { "lesson-a": "module-a", "lesson-b": "module-b" } };
  assert.deepEqual(filterQuestions(questions, { moduleId: "module-a", lessonId: "lesson-a", objectiveId: "objective-a", topic: "PAGING", type: "mcq", difficulty: "easy", bloomLevel: "remember", origin: "generated", eligibility: "eligible", bookmarkedIds: ["gq-one"], bookmarked: true, mistakeIds: ["gq-one"], mistake: true, search: "CAFE\u0301" }, indexes).map((item) => item.id), ["gq-one"]);
  assert.deepEqual(filterQuestions(questions, { review: "needs-review" }, indexes).map((item) => item.id), ["gq-two"]);
  assert.deepEqual(filterQuestions(questions, { eligibility: "ineligible" }, indexes).map((item) => item.id), ["gq-two"]);
  assert.deepEqual(filterQuestions(questions, {}, indexes).map((item) => item.id), ["gq-one", "gq-two"]);
  assert.deepEqual(filterQuestions(questions, { order: (items) => [...items].reverse() }, indexes).map((item) => item.id), ["gq-two", "gq-one"]);
});

test("scores only exact MCQ and true-false response types without coercion", () => {
  const mcq = { id: "gq-mcq", origin: "generated", type: "mcq", options: ["a", "b", "c", "d"], correctAnswer: 0, needsReview: false, review: { status: "validated" }, qualityState: "validated", reviewState: "unreviewed", duplicateDisposition: "retain", sourceRefs: [{ sourceId: "os-lec-01" }] };
  const trueFalse = { ...mcq, id: "gq-tf", type: "true-false", correctAnswer: false };
  assert.deepEqual(scoreResponse(mcq, 0), { answered: true, valid: true, scored: true, correct: true, correctAnswer: 0 });
  assert.deepEqual(scoreResponse(trueFalse, false), { answered: true, valid: true, scored: true, correct: true, correctAnswer: false });
  for (const invalid of ["0", "true", 4, true, null]) { const result = scoreResponse(mcq, invalid); assert.equal(result.answered, false); assert.equal(result.valid, false); assert.equal(result.correct, null); }
  assert.equal(scoreResponse(trueFalse, 0).valid, false);
  assert.equal(scoreResponse({ ...mcq, needsReview: true }, 0).scored, false);
});
