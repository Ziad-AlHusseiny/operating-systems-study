import assert from "node:assert/strict";
import { readFile } from "node:fs/promises";
import test from "node:test";

import { filterLessons, loadCourseData } from "../js/data.js";
import { filterQuestions, scoreResponse } from "../js/questions.js";

const projectId = "operating-systems-study";
const clone = (value) => structuredClone(value);
const root = new URL("../", import.meta.url);
const publicPayloads = Object.fromEntries(await Promise.all([
  "course.json", "lessons.json", "questions.json", "explanations-ar.json",
].map(async (name) => [name, JSON.parse(await readFile(new URL(`data/${name}`, root), "utf8"))])));

function evidenceFor(type, correctAnswer) {
  const targets = type === "mcq"
   ? ["prompt", "correctAnswer", "rationale", "options[0]", "options[1]", "options[2]", "options[3]", "distractorRationales[0]", "distractorRationales[1]", "distractorRationales[2]", "distractorRationales[3]"]
    : ["prompt", "correctAnswer", "rationale", ...(correctAnswer === false ? ["correctedStatement"] : [])];
  return targets.map((target, index) => ({ claimId: `claim-${index}`, target, support: index === 0 ? "direct" : "derived", sourceRefs: [{ sourceId: "os-lec-01" }] }));
}

function eligibleFields(type = "mcq", correctAnswer) {
  return {
    contentVersion: "1.0.0",
    reviewNotes: "",
    rationale: "Evidence-based rationale.",
    distractorRationales: type === "mcq" ? ["one", "two", "three", "four"] : undefined,
    evidenceMap: evidenceFor(type, correctAnswer),
  };
}

function payloads() {
  return clone(publicPayloads);
}

function response(body, { ok = true, status = 200 } = {}) { return { ok, status, json: async () => clone(body) }; }

test("loads all four payloads in parallel, builds links, and isolates returned data", async () => {
  const fixture = payloads();
  const calls = [];
  const data = await loadCourseData({ baseUrl: "/os-data/", fetchImpl: async (url) => { calls.push(url); return response(fixture[url.replace("/os-data/", "")]); } });
  assert.deepEqual(calls.sort(), ["/os-data/course.json", "/os-data/explanations-ar.json", "/os-data/lessons.json", "/os-data/questions.json"]);
  assert.equal(data.moduleById["module-os-ch01"].title, "Chapter 1: Introduction");
  assert.equal(data.objectiveToLesson["objective-os-ch01-part1-1"], "lesson-os-ch01-part1");
  assert.equal(data.lessonToModule["lesson-os-ch01-part1"], "module-os-ch01");
  assert.equal(data.questionById["gq-os-ch01-part1-001"].id, "gq-os-ch01-part1-001");
  assert.equal(data.explanationByQuestionId["gq-os-ch01-part1-001"].id, "explanation-gq-os-ch01-part1-001-ar");
  assert.throws(() => { data.questions[0].topic = "changed"; }, TypeError);
  const next = await loadCourseData({ fetchImpl: async (url) => response(fixture[url.replace("./data/", "")]) });
  assert.equal(next.questions[0].topic, "Operating-system goals");
});

test("rejects failed responses, malformed roots, and mismatched or broken links", async () => {
  await assert.rejects(loadCourseData({ fetchImpl: async () => response({}, { ok: false, status: 503 }) }), /503/);
  const malformed = payloads(); malformed["questions.json"].questions = {};
  await assert.rejects(loadCourseData({ fetchImpl: async (url) => response(malformed[url.replace("./data/", "")]) }), /questions/i);
  const mismatch = payloads(); mismatch["lessons.json"].projectId = "another-project";
  await assert.rejects(loadCourseData({ fetchImpl: async (url) => response(mismatch[url.replace("./data/", "")]) }), /project/i);
  const broken = payloads(); broken["questions.json"].questions[0].learningObjectiveId = "objective-missing";
  await assert.rejects(loadCourseData({ fetchImpl: async (url) => response(broken[url.replace("./data/", "")]) }), /objective/i);
  const missingExplanation = payloads(); delete missingExplanation["questions.json"].questions[0].generatedExplanationId;
  await assert.rejects(loadCourseData({ fetchImpl: async (url) => response(missingExplanation[url.replace("./data/", "")]) }), /explanation/i);
 const mismatchedExplanation = payloads(); mismatchedExplanation["explanations-ar.json"].explanations[0].contentVersion = "2.0.0";
 await assert.rejects(loadCourseData({ fetchImpl: async (url) => response(mismatchedExplanation[url.replace("./data/", "")]) }), /version|explanation/i);
 const nonArabicExplanation = payloads(); nonArabicExplanation["explanations-ar.json"].explanations[0].language = "en";
 await assert.rejects(loadCourseData({ fetchImpl: async (url) => response(nonArabicExplanation[url.replace("./data/", "")]) }), /Arabic|explanation/i);
});

test("rejects malformed public record contracts before the application can render", async () => {
  const load = async (fixture) => loadCourseData({ fetchImpl: async (url) => response(fixture[url.replace("./data/", "")]) });
  const cases = [
    ["unknown public root key", (fixture) => { fixture["course.json"].extra = true; }, /unexpected|contract/i],
    ["duplicate module ID", (fixture) => { fixture["course.json"].modules[1].id = fixture["course.json"].modules[0].id; }, /duplicate module/i],
    ["short MCQ options", (fixture) => { fixture["questions.json"].questions.find((item) => item.type === "mcq").options.pop(); }, /MCQ|option/i],
    ["out of bounds MCQ answer", (fixture) => { fixture["questions.json"].questions.find((item) => item.type === "mcq").correctAnswer = 4; }, /MCQ|answer/i],
    ["invalid true false type", (fixture) => { fixture["questions.json"].questions.find((item) => item.type === "true-false").type = "boolean"; }, /type/i],
    ["malformed section learner field", (fixture) => { fixture["lessons.json"].lessons[0].materialSections[0].terms[0].definition = ""; }, /term|section/i],
    ["incomplete explanation paragraphs", (fixture) => { fixture["explanations-ar.json"].explanations[0].explanation = ["فقرة واحدة"]; }, /paragraph|explanation/i],
    ["missing explanation source references", (fixture) => { fixture["explanations-ar.json"].explanations[0].sourceRefs = []; }, /source|explanation/i],
    ["invalid explanation review", (fixture) => { fixture["explanations-ar.json"].explanations[0].review = { status: "draft" }; }, /review|explanation/i],
  ];
  for (const [label, mutate, expected] of cases) {
    const fixture = payloads();
    mutate(fixture);
    await assert.rejects(load(fixture), expected, label);
  }
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

test("material search covers learner-facing objectives and nested section study text with stable AND filtering", () => {
  const lessons = [
    {
      id: "lesson-one", moduleId: "module-a", title: "Overview", objectiveIds: ["objective-one"],
      learningObjectives: [{ text: "Trace a Unicode Caf\u00e9 objective" }],
      materialSections: [{ title: "Scheduling section", summaries: [{ body: "Summary only" }], terms: [{ term: "Ready queue", definition: "A queue of ready processes" }], examples: [{ title: "Short trace", body: "Example text" }], mistakes: [{ misconception: "Wrong order", correction: "Use the ready queue" }], examTips: [{ body: "Tip only" }], recaps: [{ body: "Recap only" }], sourceRefs: [{ sourceId: "os-lec-01" }] }],
    },
    {
      id: "lesson-two", moduleId: "module-a", title: "Other", objectiveIds: ["objective-two"],
      learningObjectives: [{ text: "Different objective" }],
      materialSections: [{ title: "Other section", summaries: [], terms: [], examples: [], mistakes: [], examTips: [], recaps: [{ body: "Recap only" }], sourceRefs: [{ sourceId: "os-lec-02" }] }],
    },
  ];
  assert.deepEqual(filterLessons(lessons, { search: "CAFE\u0301" }).map((item) => item.id), ["lesson-one"]);
  assert.deepEqual(filterLessons(lessons, { search: "ready queue" }).map((item) => item.id), ["lesson-one"]);
  assert.deepEqual(filterLessons(lessons, { search: "recap only", moduleId: "module-a", sourceId: "os-lec-02" }).map((item) => item.id), ["lesson-two"]);
  assert.deepEqual(filterLessons(lessons, { search: "recap only", moduleId: "module-a" }).map((item) => item.id), ["lesson-one", "lesson-two"]);
  const searchContext = { modules: [{ id: "module-a", title: "OS Foundations" }], sources: [{ id: "os-lec-01", label: "Professor scheduling slides" }, { id: "os-lec-02", label: "Memory lecture" }] };
  assert.deepEqual(filterLessons(lessons, { search: "PROFESSOR SCHEDULING" }, searchContext).map((item) => item.id), ["lesson-one"]);
  assert.deepEqual(filterLessons(lessons, { search: "os foundations" }, searchContext).map((item) => item.id), ["lesson-one", "lesson-two"]);
});

test("filters questions with AND semantics, state IDs, normalized search, stable order, and injected ordering", () => {
  const questions = [
    { id: "gq-one", origin: "generated", type: "mcq", topic: "PAGING", prompt: "Caf\u00e9 page table", options: ["a", "b", "c", "d"], correctAnswer: 0, learningObjectiveId: "objective-a", difficulty: "easy", bloomLevel: "remember", needsReview: false, review: { status: "validated" }, qualityState: "validated", reviewState: "unreviewed", duplicateDisposition: "retain", sourceRefs: [{ sourceId: "os-lec-01" }], ...eligibleFields() },
    { id: "gq-two", origin: "generated", type: "true-false", topic: "Scheduling", prompt: "Round robin uses a quantum.", correctAnswer: true, correctedStatement: null, learningObjectiveId: "objective-b", difficulty: "hard", bloomLevel: "analyze", needsReview: true, review: { status: "needs-review" }, qualityState: "needs-review", reviewState: "needs-review", duplicateDisposition: "needs-review", sourceRefs: [{ sourceId: "os-lec-02" }], ...eligibleFields("true-false") },
  ];
  const indexes = { objectiveToLesson: { "objective-a": "lesson-a", "objective-b": "lesson-b" }, lessonToModule: { "lesson-a": "module-a", "lesson-b": "module-b" } };
  assert.deepEqual(filterQuestions(questions, { moduleId: "module-a", lessonId: "lesson-a", objectiveId: "objective-a", topic: "PAGING", type: "mcq", difficulty: "easy", bloomLevel: "remember", origin: "generated", eligibility: "eligible", bookmarkedIds: ["gq-one"], bookmarked: true, mistakeIds: ["gq-one"], mistake: true, search: "CAFE\u0301" }, indexes).map((item) => item.id), ["gq-one"]);
  assert.deepEqual(filterQuestions(questions, { review: "needs-review" }, indexes).map((item) => item.id), ["gq-two"]);
  assert.deepEqual(filterQuestions(questions, { eligibility: "ineligible" }, indexes).map((item) => item.id), ["gq-two"]);
  assert.deepEqual(filterQuestions(questions, { bookmarkedIds: [] }, indexes).map((item) => item.id), []);
  assert.deepEqual(filterQuestions(questions, { mistakeIds: ["gq-one"] }, indexes).map((item) => item.id), ["gq-one"]);
  assert.deepEqual(filterQuestions(questions, { mistakeIds: [] }, indexes).map((item) => item.id), []);
  assert.deepEqual(filterQuestions(questions, {}, indexes).map((item) => item.id), ["gq-one", "gq-two"]);
  assert.deepEqual(filterQuestions(questions, { order: (items) => [...items].reverse() }, indexes).map((item) => item.id), ["gq-two", "gq-one"]);
});

test("leaves question status unrestricted when the UI passes absent bookmark and mistake collections", () => {
  const questions = [
    { id: "gq-one", origin: "generated", type: "mcq", topic: "PAGING", prompt: "First question", options: ["a", "b", "c", "d"], correctAnswer: 0, learningObjectiveId: "objective-a", difficulty: "easy", bloomLevel: "remember", needsReview: false, review: { status: "validated" }, qualityState: "validated", reviewState: "unreviewed", duplicateDisposition: "retain", sourceRefs: [{ sourceId: "os-lec-01" }], ...eligibleFields() },
    { id: "gq-two", origin: "generated", type: "true-false", topic: "Scheduling", prompt: "Second question", correctAnswer: true, correctedStatement: null, learningObjectiveId: "objective-b", difficulty: "hard", bloomLevel: "analyze", needsReview: false, review: { status: "validated" }, qualityState: "validated", reviewState: "unreviewed", duplicateDisposition: "retain", sourceRefs: [{ sourceId: "os-lec-02" }], ...eligibleFields("true-false", true) },
  ];
  const indexes = { objectiveToLesson: { "objective-a": "lesson-a", "objective-b": "lesson-b" }, lessonToModule: { "lesson-a": "module-a", "lesson-b": "module-b" } };
  const uiFilters = { status: "all", bookmarkedIds: undefined, mistakeIds: undefined };
  assert.deepEqual(filterQuestions(questions, uiFilters, indexes).map((question) => question.id), ["gq-one", "gq-two"]);
});

test("scores only exact MCQ and true-false response types without coercion", () => {
  const mcq = { id: "gq-mcq", origin: "generated", type: "mcq", prompt: "Which option is correct?", options: ["a", "b", "c", "d"], correctAnswer: 0, needsReview: false, review: { status: "validated" }, qualityState: "validated", reviewState: "unreviewed", duplicateDisposition: "retain", sourceRefs: [{ sourceId: "os-lec-01" }], ...eligibleFields() };
  const trueFalse = { ...mcq, id: "gq-tf", type: "true-false", correctAnswer: false, correctedStatement: "The statement is false.", ...eligibleFields("true-false", false) };
  assert.deepEqual(scoreResponse(mcq, 0), { answered: true, valid: true, scored: true, correct: true, correctAnswer: 0 });
  assert.deepEqual(scoreResponse(trueFalse, false), { answered: true, valid: true, scored: true, correct: true, correctAnswer: false });
  for (const invalid of ["0", "true", 4, true, null]) { const result = scoreResponse(mcq, invalid); assert.equal(result.answered, false); assert.equal(result.valid, false); assert.equal(result.correct, null); }
  assert.equal(scoreResponse(trueFalse, 0).valid, false);
  assert.equal(scoreResponse({ ...mcq, needsReview: true }, 0).scored, false);
  for (const invalidQuestion of [
   { ...mcq, duplicateDisposition: undefined },
   { ...mcq, qualityState: "draft" },
    { ...mcq, qualityState: "approved", reviewState: "approved" },
   { ...mcq, evidenceMap: mcq.evidenceMap.filter((item) => item.target !== "options[3]") },
   { ...mcq, evidenceMap: [] },
    { ...trueFalse, evidenceMap: trueFalse.evidenceMap.filter((item) => item.target !== "correctedStatement") },
   { ...mcq, sourceRefs: [] },
    { ...mcq, correctAnswer: 4 },
  ]) {
    assert.equal(scoreResponse(invalidQuestion, 0).scored, false);
  }
});
