const PAYLOAD_FIELDS = [
  "explanations",
  "generatedStudyGuidance",
  "language",
  "version",
];
const ENTRY_FIELDS = ["explanation", "note", "translation"];

function isObject(value) {
  return value !== null && typeof value === "object" && !Array.isArray(value);
}

function hasExactFields(value, fields) {
  if (!isObject(value)) return false;
  const actual = Object.keys(value).sort();
  return actual.length === fields.length && actual.every((field, index) => field === fields[index]);
}

function invalidPayload(reason) {
  return new Error(`Invalid explanation payload: ${reason}.`);
}

export async function loadExplanations(url = "./data/explanations-ar.json") {
  const response = await fetch(url);
  if (!response.ok) {
    throw new Error(`Could not load Arabic explanations (${response.status}).`);
  }
  return response.json();
}

export function validateExplanationPayload(payload, questions) {
  if (!hasExactFields(payload, PAYLOAD_FIELDS)) {
    throw invalidPayload("unexpected top-level schema");
  }
  if (payload.version !== 1) {
    throw invalidPayload("version must be 1");
  }
  if (payload.language !== "ar") {
    throw invalidPayload("language must be ar");
  }
  if (typeof payload.generatedStudyGuidance !== "boolean") {
    throw invalidPayload("generatedStudyGuidance must be a boolean");
  }
  if (!isObject(payload.explanations)) {
    throw invalidPayload("explanations must be an object");
  }
  if (!Array.isArray(questions)) {
    throw invalidPayload("canonical questions must be an array");
  }

  const questionIds = questions.map((question) => question?.id);
  if (
    questionIds.some((questionId) => typeof questionId !== "string") ||
    new Set(questionIds).size !== questionIds.length
  ) {
    throw invalidPayload("canonical question IDs must be unique strings");
  }

  const expectedIds = new Set(questionIds);
  const explanationIds = Object.keys(payload.explanations);
  const actualIds = new Set(explanationIds);
  const missing = questionIds.filter((questionId) => !actualIds.has(questionId)).sort();
  const unknown = explanationIds.filter((questionId) => !expectedIds.has(questionId)).sort();
  if (missing.length || unknown.length) {
    throw invalidPayload(`ID mismatch: missing=${missing.join(",")}; unknown=${unknown.join(",")}`);
  }

  for (const [questionId, entry] of Object.entries(payload.explanations)) {
    if (!hasExactFields(entry, ENTRY_FIELDS)) {
      throw invalidPayload(`${questionId} has an unexpected entry schema`);
    }
    if (typeof entry.translation !== "string") {
      throw invalidPayload(`${questionId} translation must be a string`);
    }
    if (
      !Array.isArray(entry.explanation) ||
      !entry.explanation.every((paragraph) => typeof paragraph === "string")
    ) {
      throw invalidPayload(`${questionId} explanation must be an array of strings`);
    }
    if (typeof entry.note !== "string") {
      throw invalidPayload(`${questionId} note must be a string`);
    }
  }

  return payload;
}

export function getExplanation(explanations, questionId) {
  if (!isObject(explanations) || !Object.hasOwn(explanations, questionId)) {
    return null;
  }
  return explanations[questionId] ?? null;
}

export function searchExplanationEntries(questions, explanations, filters = {}) {
  const search = String(filters.search || "").trim().toLocaleLowerCase();

  return questions.flatMap((question) => {
    if (
      filters.source &&
      filters.source !== "all" &&
      !question.sources?.some((source) => source.collection === filters.source)
    ) {
      return [];
    }
    if (filters.topic && filters.topic !== "all" && question.topic !== filters.topic) {
      return [];
    }
    if (filters.type && filters.type !== "all" && question.type !== filters.type) {
      return [];
    }

    const explanation = getExplanation(explanations, question.id);
    if (!explanation) return [];

    if (search) {
      const haystack = [
        question.prompt,
        explanation.translation,
        ...explanation.explanation,
        explanation.note,
      ]
        .join(" ")
        .toLocaleLowerCase();
      if (!haystack.includes(search)) return [];
    }

    return [{ question, explanation }];
  });
}
