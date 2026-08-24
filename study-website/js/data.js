function isObject(value) {
  return Boolean(value) && typeof value === "object" && !Array.isArray(value);
}

function clone(value) {
  return structuredClone(value);
}

function freeze(value, seen = new Set()) {
  if (!value || typeof value !== "object" || seen.has(value)) return value;
  seen.add(value);
  for (const item of Object.values(value)) freeze(item, seen);
  return Object.freeze(value);
}

function idIndex(records, label) {
  const index = Object.create(null);
  for (const record of records) {
    if (!isObject(record) || typeof record.id !== "string" || !record.id) {
      throw new Error(`${label} records need a stable ID.`);
    }
    if (Object.hasOwn(index, record.id)) throw new Error(`Duplicate ${label} ID: ${record.id}.`);
    index[record.id] = record;
  }
  return index;
}

function assertPayload(payload, name) {
  if (!isObject(payload)) throw new Error(`${name} has an invalid JSON root.`);
}

const ROOT_KEYS = {
  course: ["schemaVersion", "projectId", "version", "project", "modules", "objectives", "sources", "contentPolicy", "questionGeneration", "exam", "coverage"],
  lessons: ["schemaVersion", "projectId", "lessons"],
  questions: ["schemaVersion", "projectId", "questions"],
  explanations: ["schemaVersion", "projectId", "explanations"],
};
const PROJECT_AGREEMENT = {
  title: "Operating Systems Study",
  shortTitle: "OS Study",
  slug: "operating-systems-study",
  description: "A bilingual, source-backed Operating Systems study and exam website.",
  brandInitials: "OS",
  sourceLanguage: "en",
  studyLanguage: "ar",
};
const POLICY_AGREEMENT = { mode: "source-plus-generated", allowOutsideSources: false, generatedQuestionsRequireHumanReviewForExam: false };
const QUESTION_GENERATION_AGREEMENT = {
  mcqPerLesson: 6,
  trueFalsePerLesson: 4,
  difficultyPercent: { easy: 30, medium: 50, hard: 20 },
  bloomPercent: { remember: 30, apply: 50, analyze: 20 },
};
const EXAM_AGREEMENT = { defaultCount: 25, defaultMinutes: 30 };
const MODULE_KEYS = ["id", "title", "order", "objectiveIds", "sourceRefs"];
const OBJECTIVE_KEYS = ["id", "moduleId", "text", "order", "sourceRefs"];
const LESSON_KEYS = ["id", "moduleId", "objectiveIds", "title", "contentVersion", "materialSectionIds", "learningObjectives", "materialSections", "needsReview", "reviewNotes", "review"];
const SECTION_KEYS = ["id", "lessonId", "order", "title", "origin", "label", "generatedStudyGuidance", "summaries", "terms", "examples", "mistakes", "examTips", "recaps", "sourceRefs", "linkedQuestionIds", "contentVersion", "needsReview", "reviewNotes"];
const BASE_QUESTION_KEYS = ["id", "origin", "type", "prompt", "topic", "difficulty", "bloomLevel", "cognitiveLevel", "learningObjectiveId", "sourceRefs", "generationMethod", "generatedExplanationId", "provenance", "contentVersion", "qualityState", "reviewState", "duplicateComparison", "duplicateDisposition", "needsReview", "reviewNotes", "review", "correctAnswer", "rationale", "evidenceMap"];
const EXPLANATION_KEYS = ["id", "questionId", "language", "generatedStudyGuidance", "translation", "explanation", "body", "note", "contentVersion", "sourceRefs", "needsReview", "reviewNotes", "review"];

function assertExactKeys(value, keys, label) {
  if (!isObject(value)) throw new Error(`${label} must be an object.`);
  const actual = Object.keys(value).sort();
  const expected = [...keys].sort();
  if (actual.length !== expected.length || actual.some((key, index) => key !== expected[index])) {
    throw new Error(`${label} has an unexpected or missing key.`);
  }
}

function assertNonEmptyString(value, label) {
  if (typeof value !== "string" || !value.trim()) throw new Error(`${label} must be a non-empty string.`);
}

function assertArray(value, label, { nonEmpty = false } = {}) {
  if (!Array.isArray(value) || (nonEmpty && !value.length)) throw new Error(`${label} must be ${nonEmpty ? "a non-empty" : "an"} array.`);
}

function assertExactValue(value, expected, label) {
  const matches = function (actual, wanted) {
    if (actual === wanted) return true;
    if (Array.isArray(actual) || Array.isArray(wanted)) return Array.isArray(actual) && Array.isArray(wanted) && actual.length === wanted.length && actual.every((item, index) => matches(item, wanted[index]));
    if (!isObject(actual) || !isObject(wanted)) return false;
    const actualKeys = Object.keys(actual);
    const expectedKeys = Object.keys(wanted);
    return actualKeys.length === expectedKeys.length && expectedKeys.every((key) => Object.hasOwn(actual, key) && matches(actual[key], wanted[key]));
  };
  if (!matches(value, expected)) throw new Error(`${label} does not match the Operating Systems Study project agreement.`);
}

function assertStableId(value, label, expression) {
  assertNonEmptyString(value, label);
  if (expression && !expression.test(value)) throw new Error(`${label} is not a canonical stable ID.`);
}

function assertStrictAscending(records, label) {
  let previous = -Infinity;
  for (const record of records) {
    if (!Number.isInteger(record.order) || record.order <= previous) throw new Error(`${label} must use a stable ascending order.`);
    previous = record.order;
  }
}

function validateSourceRefs(refs, label, sourceIds) {
  assertArray(refs, `${label} source references`, { nonEmpty: true });
  for (const ref of refs) {
    assertExactKeys(ref, ["sourceId", "locationType", "location"], `${label} source reference`);
    assertNonEmptyString(ref.sourceId, `${label} source ID`);
    if (sourceIds && !sourceIds.has(ref.sourceId)) throw new Error(`${label} references an unavailable source.`);
    if (ref.locationType !== "page" || !Number.isInteger(ref.location) || ref.location < 1) throw new Error(`${label} has an invalid source location.`);
  }
}

function validateReview(record, label) {
  if (record.needsReview !== false || typeof record.reviewNotes !== "string") throw new Error(`${label} has an invalid review state.`);
  assertExactKeys(record.review, ["status"], `${label} review`);
  if (record.review.status !== "validated") throw new Error(`${label} requires a validated review.`);
}

function validateClaims(entries, label, sourceIds, keys) {
  assertArray(entries, label);
  for (const entry of entries) {
    assertExactKeys(entry, keys, label);
    for (const key of keys) {
      if (key === "sourceRefs") validateSourceRefs(entry[key], label, sourceIds);
      else assertNonEmptyString(entry[key], `${label} ${key}`);
    }
  }
}

function validateSection(section, sourceIds) {
  assertExactKeys(section, SECTION_KEYS, `Material section ${section?.id ?? ""}`);
  assertStableId(section.id, "Material section ID", /^material-section-os-ch\d\d-part\d-[a-z0-9-]+$/);
  assertStableId(section.lessonId, `Material section ${section.id} lesson ID`, /^lesson-os-ch\d\d-part\d$/);
  if (!Number.isInteger(section.order) || section.order < 1) throw new Error(`Material section ${section.id} has an invalid order.`);
  for (const key of ["title", "label", "contentVersion"]) assertNonEmptyString(section[key], `Material section ${section.id} ${key}`);
  if (!["source", "generated"].includes(section.origin) || section.generatedStudyGuidance !== (section.origin === "generated")) throw new Error(`Material section ${section.id} has an invalid origin.`);
  validateClaims(section.summaries, `Material section ${section.id} summaries`, sourceIds, ["body", "sourceRefs"]);
  validateClaims(section.terms, `Material section ${section.id} terms`, sourceIds, ["term", "definition", "sourceRefs"]);
  validateClaims(section.examples, `Material section ${section.id} examples`, sourceIds, ["title", "body", "sourceRefs"]);
  validateClaims(section.mistakes, `Material section ${section.id} mistakes`, sourceIds, ["misconception", "correction", "sourceRefs"]);
  validateClaims(section.examTips, `Material section ${section.id} exam tips`, sourceIds, ["body", "sourceRefs"]);
  validateClaims(section.recaps, `Material section ${section.id} recaps`, sourceIds, ["body", "sourceRefs"]);
  validateSourceRefs(section.sourceRefs, `Material section ${section.id}`, sourceIds);
  assertArray(section.linkedQuestionIds, `Material section ${section.id} linked question IDs`);
  for (const id of section.linkedQuestionIds) assertStableId(id, `Material section ${section.id} linked question ID`, /^gq-os-ch\d\d-part\d-\d{3}$/);
  if (section.needsReview !== false || typeof section.reviewNotes !== "string") throw new Error(`Material section ${section.id} has an invalid review state.`);
}

function validateQuestion(question, sourceIds) {
  if (!["mcq", "true-false"].includes(question?.type)) throw new Error(`Question ${question?.id ?? ""} has an invalid type.`);
  if (question?.origin === "generated" && (typeof question.generatedExplanationId !== "string" || !question.generatedExplanationId)) throw new Error(`Generated question ${question?.id ?? ""} has a missing explanation link.`);
  const questionKeys = question.type === "mcq" ? [...BASE_QUESTION_KEYS, "options", "distractorRationales"] : [...BASE_QUESTION_KEYS, "correctedStatement"];
  assertExactKeys(question, questionKeys, `Question ${question?.id ?? ""}`);
  assertStableId(question.id, "Question ID", /^gq-os-ch\d\d-part\d-\d{3}$/);
  for (const key of ["origin", "prompt", "topic", "difficulty", "bloomLevel", "cognitiveLevel", "learningObjectiveId", "generationMethod", "generatedExplanationId", "contentVersion", "qualityState", "reviewState", "duplicateDisposition", "rationale"]) assertNonEmptyString(question[key], `Question ${question.id} ${key}`);
  if (question.origin !== "generated" || !["easy", "medium", "hard"].includes(question.difficulty) || !["remember", "apply", "analyze"].includes(question.bloomLevel) || question.cognitiveLevel !== question.bloomLevel || question.qualityState !== "validated" || question.reviewState !== "unreviewed" || question.duplicateDisposition !== "retain") throw new Error(`Question ${question.id} has an invalid generated-question policy.`);
  assertStableId(question.learningObjectiveId, `Question ${question.id} objective ID`, /^objective-os-ch\d\d-part\d-\d$/);
  assertStableId(question.generatedExplanationId, `Question ${question.id} explanation ID`, /^explanation-gq-os-ch\d\d-part\d-\d{3}-ar$/);
  validateSourceRefs(question.sourceRefs, `Question ${question.id}`, sourceIds);
  validateReview(question, `Question ${question.id}`);
  assertExactKeys(question.provenance, ["sourceRefs", "modelVersion", "promptVersion"], `Question ${question.id} provenance`);
  validateSourceRefs(question.provenance.sourceRefs, `Question ${question.id} provenance`, sourceIds);
  assertNonEmptyString(question.provenance.modelVersion, `Question ${question.id} model version`);
  assertNonEmptyString(question.provenance.promptVersion, `Question ${question.id} prompt version`);
  assertExactKeys(question.duplicateComparison, ["algorithmVersion", "normalizedPrompt", "candidateIds", "matchClass"], `Question ${question.id} duplicate comparison`);
  assertNonEmptyString(question.duplicateComparison.algorithmVersion, `Question ${question.id} duplicate algorithm version`);
  assertNonEmptyString(question.duplicateComparison.normalizedPrompt, `Question ${question.id} normalized prompt`);
  assertArray(question.duplicateComparison.candidateIds, `Question ${question.id} duplicate candidates`);
  if (question.duplicateComparison.matchClass !== "none" || question.duplicateComparison.candidateIds.length) throw new Error(`Question ${question.id} has an invalid duplicate disposition.`);
  if (question.type === "mcq") {
    assertArray(question.options, `Question ${question.id} MCQ options`, { nonEmpty: true });
    if (question.options.length !== 4 || question.options.some((option) => typeof option !== "string" || !option.trim()) || new Set(question.options).size !== 4 || !Number.isInteger(question.correctAnswer) || question.correctAnswer < 0 || question.correctAnswer >= 4) throw new Error(`Question ${question.id} has an invalid MCQ option or answer index.`);
    assertArray(question.distractorRationales, `Question ${question.id} distractor rationales`);
    if (question.distractorRationales.length !== 4 || question.distractorRationales.some((value) => typeof value !== "string" || !value.trim())) throw new Error(`Question ${question.id} has invalid MCQ distractor rationales.`);
  } else if (typeof question.correctAnswer !== "boolean" || (question.correctAnswer ? question.correctedStatement !== null : typeof question.correctedStatement !== "string" || !question.correctedStatement.trim())) {
    throw new Error(`Question ${question.id} has an invalid true-false answer.`);
  }
  assertArray(question.evidenceMap, `Question ${question.id} evidence`, { nonEmpty: true });
  const requiredTargets = question.type === "mcq" ? ["prompt", "correctAnswer", "rationale", "options[0]", "options[1]", "options[2]", "options[3]", "distractorRationales[0]", "distractorRationales[1]", "distractorRationales[2]", "distractorRationales[3]"] : ["prompt", "correctAnswer", "rationale", ...(question.correctAnswer ? [] : ["correctedStatement"])];
  if (question.evidenceMap.length !== requiredTargets.length) throw new Error(`Question ${question.id} has incomplete evidence.`);
  const targets = new Set();
  for (const evidence of question.evidenceMap) {
    assertExactKeys(evidence, ["claimId", "target", "sourceRefs", "support"], `Question ${question.id} evidence`);
    assertNonEmptyString(evidence.claimId, `Question ${question.id} evidence claim ID`);
    assertNonEmptyString(evidence.target, `Question ${question.id} evidence target`);
    if (targets.has(evidence.target) || !requiredTargets.includes(evidence.target) || !["direct", "derived"].includes(evidence.support)) throw new Error(`Question ${question.id} has an invalid evidence target.`);
    targets.add(evidence.target);
    validateSourceRefs(evidence.sourceRefs, `Question ${question.id} evidence`, sourceIds);
  }
}

function validatePublicContract(course, lessonsPayload, questionsPayload, explanationsPayload) {
  assertExactKeys(course, ROOT_KEYS.course, "course.json");
  assertExactKeys(lessonsPayload, ROOT_KEYS.lessons, "lessons.json");
  assertExactKeys(questionsPayload, ROOT_KEYS.questions, "questions.json");
  assertExactKeys(explanationsPayload, ROOT_KEYS.explanations, "explanations-ar.json");
  for (const [name, payload] of Object.entries({ course, lessons: lessonsPayload, questions: questionsPayload, explanations: explanationsPayload })) {
    if (payload.schemaVersion !== "1" || payload.projectId !== PROJECT_AGREEMENT.slug) throw new Error(`${name}.json does not match the Operating Systems Study project agreement.`);
  }
  if (course.version !== "1.0.0") throw new Error("course.json has an invalid content version.");
  assertExactKeys(course.project, Object.keys(PROJECT_AGREEMENT), "course.json project");
  assertExactValue(course.project, PROJECT_AGREEMENT, "course.json project");
  assertExactKeys(course.contentPolicy, Object.keys(POLICY_AGREEMENT), "course.json content policy");
  assertExactValue(course.contentPolicy, POLICY_AGREEMENT, "course.json content policy");
  assertExactKeys(course.questionGeneration, Object.keys(QUESTION_GENERATION_AGREEMENT), "course.json question generation");
  assertExactValue(course.questionGeneration, QUESTION_GENERATION_AGREEMENT, "course.json question generation");
  assertExactKeys(course.exam, Object.keys(EXAM_AGREEMENT), "course.json exam");
  assertExactValue(course.exam, EXAM_AGREEMENT, "course.json exam");
  assertExactKeys(course.coverage, ["totalPages", "teachingPages", "classificationCounts", "teachingPageIds", "referencedTeachingPages"], "course.json coverage");
  if (course.coverage.totalPages !== 517 || course.coverage.teachingPages !== 454 || !isObject(course.coverage.classificationCounts) || !Array.isArray(course.coverage.teachingPageIds) || !Array.isArray(course.coverage.referencedTeachingPages)) throw new Error("course.json has invalid coverage.");
  assertArray(course.sources, "course.json sources", { nonEmpty: true });
  const sourceIds = new Set();
  for (const source of course.sources) {
    assertExactKeys(source, ["id", "fileName", "collection", "label", "format", "pages", "checksum", "locations", "status"], "course source");
    assertStableId(source.id, "Course source ID", /^os-lec-\d{2}$/);
    if (sourceIds.has(source.id)) throw new Error(`Duplicate source ID: ${source.id}.`);
    sourceIds.add(source.id);
    for (const key of ["fileName", "collection", "label", "checksum"]) assertNonEmptyString(source[key], `Course source ${source.id} ${key}`);
    if (source.format !== "pdf" || source.status !== "accepted" || !Number.isInteger(source.pages) || source.pages < 1) throw new Error(`Course source ${source.id} has an invalid public record.`);
    assertArray(source.locations, `Course source ${source.id} locations`, { nonEmpty: true });
    for (const location of source.locations) {
      assertExactKeys(location, ["locationType", "location"], `Course source ${source.id} location`);
      if (location.locationType !== "page" || !Number.isInteger(location.location) || location.location < 1 || location.location > source.pages) throw new Error(`Course source ${source.id} has an invalid location.`);
    }
  }
  assertArray(course.modules, "course.json modules", { nonEmpty: true });
  assertArray(course.objectives, "course.json objectives", { nonEmpty: true });
  assertStrictAscending(course.modules, "course modules");
  for (const module of course.modules) {
    assertExactKeys(module, MODULE_KEYS, `Module ${module?.id ?? ""}`);
    assertStableId(module.id, "Module ID", /^module-os-ch\d\d$/);
    assertNonEmptyString(module.title, `Module ${module.id} title`);
    assertArray(module.objectiveIds, `Module ${module.id} objective IDs`, { nonEmpty: true });
    for (const id of module.objectiveIds) assertStableId(id, `Module ${module.id} objective ID`, /^objective-os-ch\d\d-part\d-\d$/);
    validateSourceRefs(module.sourceRefs, `Module ${module.id}`, sourceIds);
  }
  for (const objective of course.objectives) {
    assertExactKeys(objective, OBJECTIVE_KEYS, `Objective ${objective?.id ?? ""}`);
    assertStableId(objective.id, "Objective ID", /^objective-os-ch\d\d-part\d-\d$/);
    assertStableId(objective.moduleId, `Objective ${objective.id} module ID`, /^module-os-ch\d\d$/);
    assertNonEmptyString(objective.text, `Objective ${objective.id} text`);
    if (!Number.isInteger(objective.order) || objective.order < 1) throw new Error(`Objective ${objective.id} has an invalid order.`);
    validateSourceRefs(objective.sourceRefs, `Objective ${objective.id}`, sourceIds);
  }
  assertArray(lessonsPayload.lessons, "lessons.json lessons", { nonEmpty: true });
  for (const lesson of lessonsPayload.lessons) {
    assertExactKeys(lesson, LESSON_KEYS, `Lesson ${lesson?.id ?? ""}`);
    assertStableId(lesson.id, "Lesson ID", /^lesson-os-ch\d\d-part\d$/);
    assertStableId(lesson.moduleId, `Lesson ${lesson.id} module ID`, /^module-os-ch\d\d$/);
    for (const key of ["title", "contentVersion"]) assertNonEmptyString(lesson[key], `Lesson ${lesson.id} ${key}`);
    validateReview(lesson, `Lesson ${lesson.id}`);
    assertArray(lesson.objectiveIds, `Lesson ${lesson.id} objective IDs`, { nonEmpty: true });
    assertArray(lesson.learningObjectives, `Lesson ${lesson.id} learning objectives`, { nonEmpty: true });
    if (lesson.objectiveIds.length !== lesson.learningObjectives.length) throw new Error(`Lesson ${lesson.id} has mismatched objectives.`);
    for (const objective of lesson.learningObjectives) {
      assertExactKeys(objective, OBJECTIVE_KEYS, `Lesson ${lesson.id} learning objective`);
      assertNonEmptyString(objective.text, `Lesson ${lesson.id} learning objective text`);
      validateSourceRefs(objective.sourceRefs, `Lesson ${lesson.id} learning objective`, sourceIds);
    }
    assertArray(lesson.materialSectionIds, `Lesson ${lesson.id} material section IDs`, { nonEmpty: true });
    assertArray(lesson.materialSections, `Lesson ${lesson.id} material sections`, { nonEmpty: true });
    if (lesson.materialSectionIds.length !== lesson.materialSections.length) throw new Error(`Lesson ${lesson.id} has mismatched material sections.`);
    assertStrictAscending(lesson.materialSections, `Lesson ${lesson.id} material sections`);
    for (let index = 0; index < lesson.materialSections.length; index += 1) {
      const section = lesson.materialSections[index];
      validateSection(section, sourceIds);
      if (section.lessonId !== lesson.id || section.id !== lesson.materialSectionIds[index]) throw new Error(`Lesson ${lesson.id} has a broken material section link.`);
    }
  }
  assertArray(questionsPayload.questions, "questions.json questions", { nonEmpty: true });
  for (const question of questionsPayload.questions) validateQuestion(question, sourceIds);
  assertArray(explanationsPayload.explanations, "explanations-ar.json explanations", { nonEmpty: true });
  for (const explanation of explanationsPayload.explanations) {
    assertExactKeys(explanation, EXPLANATION_KEYS, `Explanation ${explanation?.id ?? ""}`);
    assertStableId(explanation.id, "Explanation ID", /^explanation-gq-os-ch\d\d-part\d-\d{3}-ar$/);
    assertStableId(explanation.questionId, `Explanation ${explanation.id} question ID`, /^gq-os-ch\d\d-part\d-\d{3}$/);
    if (explanation.language !== "ar" || explanation.generatedStudyGuidance !== true) throw new Error(`Explanation ${explanation.id} must be Arabic generated study guidance.`);
    for (const key of ["translation", "body", "note", "contentVersion"]) assertNonEmptyString(explanation[key], `Explanation ${explanation.id} ${key}`);
    assertArray(explanation.explanation, `Explanation ${explanation.id} paragraphs`, { nonEmpty: true });
    if (explanation.explanation.length < 2 || explanation.explanation.length > 3 || explanation.explanation.some((paragraph) => typeof paragraph !== "string" || !paragraph.trim()) || explanation.body !== explanation.explanation.join("\n\n")) throw new Error(`Explanation ${explanation.id} has invalid Arabic paragraphs.`);
    validateSourceRefs(explanation.sourceRefs, `Explanation ${explanation.id}`, sourceIds);
    validateReview(explanation, `Explanation ${explanation.id}`);
  }
}

function dataUrl(baseUrl, name) {
  const base = baseUrl ?? "./data/";
  return base.endsWith("/") ? `${base}${name}` : `${base}/${name}`;
}

async function fetchJson(fetchImpl, url, label) {
  let response;
  try {
    response = await fetchImpl(url);
  } catch (error) {
    throw new Error(`Could not load ${label}: ${error?.message || "network failure"}.`);
  }
  if (!response?.ok) throw new Error(`Could not load ${label} (${response?.status ?? "unknown status"}).`);
  try {
    return await response.json();
  } catch (error) {
    throw new Error(`${label} contains malformed JSON: ${error?.message || "parse failure"}.`);
  }
}

function sourceIdsForLesson(lesson) {
  const refs = [
    ...(lesson.sourceRefs || []),
    ...(lesson.learningObjectives || []).flatMap((objective) => objective.sourceRefs || []),
    ...(lesson.materialSections || []).flatMap((section) => section.sourceRefs || []),
  ];
  return new Set(refs.map((ref) => ref?.sourceId).filter((id) => typeof id === "string"));
}

function validateLinks(course, lessonsPayload, questionsPayload, explanationsPayload) {
  validatePublicContract(course, lessonsPayload, questionsPayload, explanationsPayload);
  if (!isObject(course.project) || typeof course.project.slug !== "string" || !course.project.slug) {
    throw new Error("course.json has no project slug.");
  }
  const projectId = course.projectId;
  if (typeof projectId !== "string" || projectId !== course.project.slug) {
    throw new Error("course.json has a project ID mismatch.");
  }
  for (const [name, payload] of Object.entries({ lessons: lessonsPayload, questions: questionsPayload, explanations: explanationsPayload })) {
    if (payload.projectId !== projectId) throw new Error(`${name}.json has a project ID mismatch.`);
  }
  if (!Array.isArray(course.modules) || !Array.isArray(course.objectives)) {
    throw new Error("course.json must contain module and objective arrays.");
  }
  if (!Array.isArray(lessonsPayload.lessons)) throw new Error("lessons.json must contain a lessons array.");
  if (!Array.isArray(questionsPayload.questions)) throw new Error("questions.json must contain a questions array.");
  if (!Array.isArray(explanationsPayload.explanations)) throw new Error("explanations-ar.json must contain an explanations array.");

  const moduleById = idIndex(course.modules, "module");
  const objectiveById = idIndex(course.objectives, "objective");
  const lessonById = idIndex(lessonsPayload.lessons, "lesson");
  const questionById = idIndex(questionsPayload.questions, "question");
  const explanationById = idIndex(explanationsPayload.explanations, "explanation");
  const objectiveToLesson = Object.create(null);
  const lessonToModule = Object.create(null);

  for (const module of course.modules) {
    const moduleObjectives = course.objectives.filter((objective) => objective.moduleId === module.id);
    assertStrictAscending(moduleObjectives, `Objectives in ${module.id}`);
    const expectedIds = moduleObjectives.map((objective) => objective.id);
    if (module.objectiveIds.length !== expectedIds.length || module.objectiveIds.some((id, index) => id !== expectedIds[index])) {
      throw new Error(`Module ${module.id} has an out-of-order objective link.`);
    }
  }
  let previousLessonModuleOrder = -Infinity;
  let previousLessonId = "";
  const sectionIds = new Set();

  for (const objective of course.objectives) {
    if (!moduleById[objective.moduleId]) throw new Error(`Objective ${objective.id} has a missing module link.`);
  }
  for (const lesson of lessonsPayload.lessons) {
    if (!moduleById[lesson.moduleId]) throw new Error(`Lesson ${lesson.id} has a missing module link.`);
    const moduleOrder = moduleById[lesson.moduleId].order;
    if (moduleOrder < previousLessonModuleOrder || moduleOrder === previousLessonModuleOrder && lesson.id <= previousLessonId) {
      throw new Error("Lessons must remain in canonical module and lesson order.");
    }
    previousLessonModuleOrder = moduleOrder;
    previousLessonId = lesson.id;
    lessonToModule[lesson.id] = lesson.moduleId;
    if (!Array.isArray(lesson.objectiveIds)) throw new Error(`Lesson ${lesson.id} has invalid objectives.`);
    if (lesson.objectiveIds.length !== lesson.learningObjectives.length || lesson.objectiveIds.some((id, index) => id !== lesson.learningObjectives[index].id)) {
      throw new Error(`Lesson ${lesson.id} has out-of-order learning objectives.`);
    }
    for (const objectiveId of lesson.objectiveIds) {
      const objective = objectiveById[objectiveId];
      if (!objective) throw new Error(`Lesson ${lesson.id} has a missing objective link.`);
      if (objective.moduleId !== lesson.moduleId) throw new Error(`Lesson ${lesson.id} has an objective/module mismatch.`);
      if (objectiveToLesson[objectiveId]) throw new Error(`Objective ${objectiveId} is linked to more than one lesson.`);
      objectiveToLesson[objectiveId] = lesson.id;
    }
    for (const learningObjective of lesson.learningObjectives) {
      const canonicalObjective = objectiveById[learningObjective.id];
      if (!canonicalObjective || JSON.stringify(learningObjective) !== JSON.stringify(canonicalObjective)) {
        throw new Error(`Lesson ${lesson.id} has a mismatched learning objective record.`);
      }
    }
    for (const section of lesson.materialSections) {
      if (sectionIds.has(section.id)) throw new Error(`Duplicate material section ID: ${section.id}.`);
      sectionIds.add(section.id);
    }
  }
  for (const question of questionsPayload.questions) {
    const objectiveId = question.learningObjectiveId ?? question.objectiveId;
    if (!objectiveById[objectiveId]) throw new Error(`Question ${question.id} has a missing objective link.`);
    if (!objectiveToLesson[objectiveId]) throw new Error(`Question ${question.id} has a missing lesson link.`);
    if (!Array.isArray(question.sourceRefs) || !question.sourceRefs.length) {
      throw new Error(`Question ${question.id} has no evidence link.`);
    }
    if (question.origin === "generated" && (typeof question.generatedExplanationId !== "string" || !question.generatedExplanationId)) {
      throw new Error(`Generated question ${question.id} has a missing explanation link.`);
    }
    if (question.generatedExplanationId && !explanationById[question.generatedExplanationId]) {
      throw new Error(`Question ${question.id} has a missing explanation link.`);
    }
    for (const lesson of lessonsPayload.lessons) {
      for (const section of lesson.materialSections) {
        if (section.linkedQuestionIds.includes(question.id) && lesson.id !== objectiveToLesson[objectiveId]) {
          throw new Error(`Question ${question.id} is linked from a different lesson.`);
        }
      }
    }
  }
  const explanationByQuestionId = Object.create(null);
  for (const explanation of explanationsPayload.explanations) {
    if (!questionById[explanation.questionId]) throw new Error(`Explanation ${explanation.id} has a missing question link.`);
    if (explanationByQuestionId[explanation.questionId]) throw new Error(`Question ${explanation.questionId} has more than one explanation.`);
    explanationByQuestionId[explanation.questionId] = explanation;
  }
  for (const question of questionsPayload.questions) {
    if (question.origin === "generated" && (!explanationByQuestionId[question.id] || explanationByQuestionId[question.id].id !== question.generatedExplanationId || explanationByQuestionId[question.id].language !== "ar" || explanationByQuestionId[question.id].contentVersion !== question.contentVersion || JSON.stringify(explanationByQuestionId[question.id].sourceRefs) !== JSON.stringify(question.sourceRefs))) {
      throw new Error(`Question ${question.id} has a mismatched explanation link.`);
    }
  }
  return { moduleById, objectiveById, lessonById, questionById, explanationById, explanationByQuestionId, objectiveToLesson, lessonToModule };
}

export async function loadCourseData({ fetchImpl = globalThis.fetch, baseUrl } = {}) {
  if (typeof fetchImpl !== "function") throw new Error("A fetch implementation is required to load course data.");
  const [course, lessonsPayload, questionsPayload, explanationsPayload] = await Promise.all([
    fetchJson(fetchImpl, dataUrl(baseUrl, "course.json"), "course.json"),
    fetchJson(fetchImpl, dataUrl(baseUrl, "lessons.json"), "lessons.json"),
    fetchJson(fetchImpl, dataUrl(baseUrl, "questions.json"), "questions.json"),
    fetchJson(fetchImpl, dataUrl(baseUrl, "explanations-ar.json"), "explanations-ar.json"),
  ]);
  assertPayload(course, "course.json");
  assertPayload(lessonsPayload, "lessons.json");
  assertPayload(questionsPayload, "questions.json");
  assertPayload(explanationsPayload, "explanations-ar.json");
  const indexes = validateLinks(course, lessonsPayload, questionsPayload, explanationsPayload);
  return freeze({
    course: clone(course),
    modules: clone(course.modules),
    objectives: clone(course.objectives),
    lessons: clone(lessonsPayload.lessons),
    questions: clone(questionsPayload.questions),
    explanations: clone(explanationsPayload.explanations),
    ...clone(indexes),
  });
}

function normalized(value) {
  return String(value ?? "").normalize("NFKC").toLocaleLowerCase().trim().replace(/\s+/g, " ");
}

function unrestricted(value) {
  return value === undefined || value === null || value === "" || value === "all";
}

export function filterLessons(lessons, filters = {}, context = {}) {
  const sourceId = filters.sourceId ?? filters.source;
  const moduleId = filters.moduleId ?? filters.module;
  const completion = filters.completion ?? filters.status;
  const progress = filters.lessonProgress ?? filters.progress ?? {};
  const search = normalized(filters.search);
  const moduleTitles = Object.fromEntries((Array.isArray(context.modules) ? context.modules : []).map((module) => [module.id, module.title]));
  const sourceLabels = Object.fromEntries((Array.isArray(context.sources) ? context.sources : []).map((source) => [source.id, source.label]));
  return (Array.isArray(lessons) ? lessons : []).filter((lesson) => {
    if (!unrestricted(moduleId) && lesson.moduleId !== moduleId) return false;
    if (!unrestricted(sourceId) && !sourceIdsForLesson(lesson).has(sourceId)) return false;
    const status = progress[lesson.id]?.status ?? "unstarted";
    if (!unrestricted(completion) && status !== completion) return false;
    if (search && !normalized(lessonSearchCorpus(lesson, moduleTitles, sourceLabels)).includes(search)) return false;
    return true;
  });
}

function lessonSearchCorpus(lesson, moduleTitles = {}, sourceLabels = {}) {
  const sections = Array.isArray(lesson?.materialSections) ? lesson.materialSections : [];
  const text = [lesson?.title, lesson?.moduleId, moduleTitles[lesson?.moduleId], ...(lesson?.learningObjectives || []).map((objective) => objective?.text), ...(lesson?.objectiveIds || [])];
  for (const section of sections) {
    text.push(section?.title, section?.label, section?.origin, section?.generatedStudyGuidance ? "generated study guidance" : "source material");
    for (const ref of section?.sourceRefs || []) text.push(ref?.sourceId, sourceLabels[ref?.sourceId]);
    for (const entry of section?.summaries || []) text.push(entry?.body);
    for (const entry of section?.terms || []) text.push(entry?.term, entry?.definition);
    for (const entry of section?.examples || []) text.push(entry?.title, entry?.body);
    for (const entry of section?.mistakes || []) text.push(entry?.misconception, entry?.correction);
    for (const entry of section?.examTips || []) text.push(entry?.body);
    for (const entry of section?.recaps || []) text.push(entry?.body);
  }
  return text.join(" ");
}
