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

  for (const objective of course.objectives) {
    if (!moduleById[objective.moduleId]) throw new Error(`Objective ${objective.id} has a missing module link.`);
  }
  for (const lesson of lessonsPayload.lessons) {
    if (!moduleById[lesson.moduleId]) throw new Error(`Lesson ${lesson.id} has a missing module link.`);
    lessonToModule[lesson.id] = lesson.moduleId;
    if (!Array.isArray(lesson.objectiveIds)) throw new Error(`Lesson ${lesson.id} has invalid objectives.`);
    for (const objectiveId of lesson.objectiveIds) {
      const objective = objectiveById[objectiveId];
      if (!objective) throw new Error(`Lesson ${lesson.id} has a missing objective link.`);
      if (objective.moduleId !== lesson.moduleId) throw new Error(`Lesson ${lesson.id} has an objective/module mismatch.`);
      if (objectiveToLesson[objectiveId]) throw new Error(`Objective ${objectiveId} is linked to more than one lesson.`);
      objectiveToLesson[objectiveId] = lesson.id;
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
  }
  const explanationByQuestionId = Object.create(null);
  for (const explanation of explanationsPayload.explanations) {
    if (!questionById[explanation.questionId]) throw new Error(`Explanation ${explanation.id} has a missing question link.`);
    if (explanationByQuestionId[explanation.questionId]) throw new Error(`Question ${explanation.questionId} has more than one explanation.`);
    explanationByQuestionId[explanation.questionId] = explanation;
  }
  for (const question of questionsPayload.questions) {
    if (question.origin === "generated" && (!explanationByQuestionId[question.id] || explanationByQuestionId[question.id].id !== question.generatedExplanationId || explanationByQuestionId[question.id].language !== "ar" || explanationByQuestionId[question.id].contentVersion !== question.contentVersion)) {
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

export function filterLessons(lessons, filters = {}) {
  const sourceId = filters.sourceId ?? filters.source;
  const moduleId = filters.moduleId ?? filters.module;
  const completion = filters.completion ?? filters.status;
  const progress = filters.lessonProgress ?? filters.progress ?? {};
  const search = normalized(filters.search);
  return (Array.isArray(lessons) ? lessons : []).filter((lesson) => {
    if (!unrestricted(moduleId) && lesson.moduleId !== moduleId) return false;
    if (!unrestricted(sourceId) && !sourceIdsForLesson(lesson).has(sourceId)) return false;
    const status = progress[lesson.id]?.status ?? "unstarted";
    if (!unrestricted(completion) && status !== completion) return false;
    if (search && !normalized([lesson.title, ...(lesson.objectiveIds || [])].join(" ")).includes(search)) return false;
    return true;
  });
}
