const PAYLOAD_FIELDS = [
  "explanations",
  "generatedStudyGuidance",
  "language",
  "version",
];
const ENTRY_FIELDS = ["explanation", "note", "translation"];
const ARABIC = /[\u0600-\u06ff]/;
const CONFLICT = /تعارض|اختلاف|conflict/i;
const DIFFERENTIAL = /(?<![A-Za-z0-9_])Differential(?![A-Za-z0-9_])/i;
const INCREMENTAL = /(?<![A-Za-z0-9_])Incremental(?![A-Za-z0-9_])/i;
const ANSWER_SELECTION =
  /(?:الإجابة(?:\s+الصحيحة)?|الخيار\s+الصحيح)\s*(?:(?:هي|هو)\s*)?[:：=\-–—]?\s*(?<![A-Za-z0-9_])(?:Differential|Incremental)(?![A-Za-z0-9_])|(?:the\s+)?(?:correct\s+)?answer\s*(?:is\s*)?[:：=\-–—]?\s*(?<![A-Za-z0-9_])(?:Differential|Incremental)(?![A-Za-z0-9_])/i;

function isObject(value) {
  return value !== null && typeof value === "object" && !Array.isArray(value);
}

function hasExactFields(value, fields) {
  if (!isObject(value)) return false;
  const actual = Object.keys(value).sort();
  return actual.length === fields.length && actual.every((field, index) => field === fields[index]);
}

function isNonEmptyArabic(value) {
  return typeof value === "string" && value.trim().length > 0 && ARABIC.test(value);
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
  if (payload.generatedStudyGuidance !== true) {
    throw invalidPayload("generatedStudyGuidance must be true");
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
    if (!isNonEmptyArabic(entry.translation)) {
      throw invalidPayload(`${questionId} translation must be a non-empty Arabic string`);
    }
    if (!Array.isArray(entry.explanation) || ![2, 3].includes(entry.explanation.length)) {
      throw invalidPayload(`${questionId} explanation must have 2 or 3 paragraphs`);
    }
    if (!entry.explanation.every(isNonEmptyArabic)) {
      throw invalidPayload(
        `${questionId} every explanation paragraph must be a non-empty Arabic string`
      );
    }
    if (!isNonEmptyArabic(entry.note)) {
      throw invalidPayload(`${questionId} note must be a non-empty Arabic string`);
    }

    if (questionId === "q-103") {
      const combined = [entry.translation, ...entry.explanation, entry.note].join(" ");
      if (!CONFLICT.test(combined)) {
        throw invalidPayload("q-103 must mention the unresolved source conflict");
      }
      if (!DIFFERENTIAL.test(combined) || !INCREMENTAL.test(combined)) {
        throw invalidPayload("q-103 must mention both Differential and Incremental");
      }
      if (ANSWER_SELECTION.test(combined)) {
        throw invalidPayload("q-103 must not select an answer");
      }
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
