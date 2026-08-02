import test from "node:test";
import assert from "node:assert/strict";
import { readFile } from "node:fs/promises";
import {
  getExplanation,
  loadExplanations,
  searchExplanationEntries,
  validateExplanationPayload,
} from "../js/explanations.js";

const questions = JSON.parse(
  await readFile(new URL("../data/questions.json", import.meta.url), "utf8")
).questions;
const payload = JSON.parse(
  await readFile(new URL("../data/explanations-ar.json", import.meta.url), "utf8")
);
const explanations = payload.explanations;
const q103SelectionCases = JSON.parse(
  await readFile(new URL("./fixtures/q103-selection-cases.json", import.meta.url), "utf8")
);

function clonePayload() {
  return structuredClone(payload);
}

test("loads explanation JSON from the requested URL", async (t) => {
  const originalFetch = globalThis.fetch;
  t.after(() => {
    globalThis.fetch = originalFetch;
  });
  globalThis.fetch = async (url) => {
    assert.equal(url, "/fixtures/explanations.json");
    return { ok: true, status: 200, json: async () => payload };
  };

  assert.equal(await loadExplanations("/fixtures/explanations.json"), payload);
});

test("rejects an unsuccessful explanation response", async (t) => {
  const originalFetch = globalThis.fetch;
  t.after(() => {
    globalThis.fetch = originalFetch;
  });
  globalThis.fetch = async () => ({ ok: false, status: 503 });

  await assert.rejects(loadExplanations("/unavailable.json"), /503/);
});

test("accepts the delivered explanation payload", () => {
  assert.doesNotThrow(() => validateExplanationPayload(payload, questions));
});

test("rejects payloads that do not have the exact schema", () => {
  const cases = [];

  const extraTopLevelField = clonePayload();
  extraTopLevelField.extra = true;
  cases.push(extraTopLevelField);

  const missingTopLevelField = clonePayload();
  delete missingTopLevelField.generatedStudyGuidance;
  cases.push(missingTopLevelField);

  const extraEntryField = clonePayload();
  extraEntryField.explanations["q-001"].extra = "unexpected";
  cases.push(extraEntryField);

  const missingEntryField = clonePayload();
  delete missingEntryField.explanations["q-001"].note;
  cases.push(missingEntryField);

  for (const candidate of cases) {
    assert.throws(
      () => validateExplanationPayload(candidate, questions),
      /invalid explanation payload/i
    );
  }
});

test("rejects invalid metadata, object shapes, and field types", () => {
  const cases = [];

  const wrongVersion = clonePayload();
  wrongVersion.version = 2;
  cases.push(wrongVersion);

  const wrongLanguage = clonePayload();
  wrongLanguage.language = "en";
  cases.push(wrongLanguage);

  const wrongGuidanceType = clonePayload();
  wrongGuidanceType.generatedStudyGuidance = "true";
  cases.push(wrongGuidanceType);

  const wrongExplanationsShape = clonePayload();
  wrongExplanationsShape.explanations = [];
  cases.push(wrongExplanationsShape);

  const wrongEntryShape = clonePayload();
  wrongEntryShape.explanations["q-001"] = [];
  cases.push(wrongEntryShape);

  const wrongTranslationType = clonePayload();
  wrongTranslationType.explanations["q-001"].translation = 1;
  cases.push(wrongTranslationType);

  const wrongParagraphType = clonePayload();
  wrongParagraphType.explanations["q-001"].explanation = ["valid", 2];
  cases.push(wrongParagraphType);

  const wrongNoteType = clonePayload();
  wrongNoteType.explanations["q-001"].note = null;
  cases.push(wrongNoteType);

  for (const candidate of [null, ...cases]) {
    assert.throws(
      () => validateExplanationPayload(candidate, questions),
      /invalid explanation payload/i
    );
  }
});

test("rejects payloads not marked as generated study guidance", () => {
  const candidate = clonePayload();
  candidate.generatedStudyGuidance = false;

  assert.throws(
    () => validateExplanationPayload(candidate, questions),
    /generatedStudyGuidance must be true/i
  );
});

test("rejects empty translations, notes, and explanation paragraphs", () => {
  const cases = [];

  const emptyTranslation = clonePayload();
  emptyTranslation.explanations["q-001"].translation = "";
  cases.push(emptyTranslation);

  const emptyNote = clonePayload();
  emptyNote.explanations["q-001"].note = "   ";
  cases.push(emptyNote);

  const emptyParagraph = clonePayload();
  emptyParagraph.explanations["q-001"].explanation[0] = "";
  cases.push(emptyParagraph);

  for (const candidate of cases) {
    assert.throws(
      () => validateExplanationPayload(candidate, questions),
      /non-empty Arabic string/i
    );
  }
});

test("rejects non-Arabic translations, notes, and explanation paragraphs", () => {
  const cases = [];

  const englishTranslation = clonePayload();
  englishTranslation.explanations["q-001"].translation = "English only";
  cases.push(englishTranslation);

  const englishNote = clonePayload();
  englishNote.explanations["q-001"].note = "English only";
  cases.push(englishNote);

  const englishParagraph = clonePayload();
  englishParagraph.explanations["q-001"].explanation[0] = "English only";
  cases.push(englishParagraph);

  for (const candidate of cases) {
    assert.throws(
      () => validateExplanationPayload(candidate, questions),
      /non-empty Arabic string/i
    );
  }
});

test("requires exactly two or three explanation paragraphs", () => {
  const paragraphCases = [
    [],
    ["فقرة عربية واحدة."],
    [
      "فقرة عربية أولى.",
      "فقرة عربية ثانية.",
      "فقرة عربية ثالثة.",
      "فقرة عربية رابعة.",
    ],
  ];

  for (const explanation of paragraphCases) {
    const candidate = clonePayload();
    candidate.explanations["q-001"].explanation = explanation;
    assert.throws(
      () => validateExplanationPayload(candidate, questions),
      /explanation must have 2 or 3 paragraphs/i
    );
  }
});

test("q-103 requires conflict wording and standalone answer labels", () => {
  const validEntry = {
    translation: "يوجد تعارض غير محسوم بين المصدرين.",
    explanation: [
      "المصدر الأول يذكر Differential دون ترجيح.",
      "المصدر الثاني يذكر Incremental وتبقى المسألة للمراجعة.",
    ],
    note: "ملاحظة عربية للمراجعة.",
  };
  const validCandidate = clonePayload();
  validCandidate.explanations["q-103"] = validEntry;
  assert.doesNotThrow(() => validateExplanationPayload(validCandidate, questions));

  const malformedEntries = [
    { ...validEntry, translation: "يوجد مصدران للمراجعة." },
    {
      ...validEntry,
      explanation: [
        "المصدر الأول يذكر nondifferential دون ترجيح.",
        validEntry.explanation[1],
      ],
    },
    {
      ...validEntry,
      explanation: [
        validEntry.explanation[0],
        "المصدر الثاني يذكر incrementally وتبقى المسألة للمراجعة.",
      ],
    },
  ];

  for (const entry of malformedEntries) {
    const candidate = clonePayload();
    candidate.explanations["q-103"] = entry;
    assert.throws(
      () => validateExplanationPayload(candidate, questions),
      /q-103 must mention/i
    );
  }
});

test("q-103 rejects explicit Arabic and English answer selection", () => {
  for (const selection of q103SelectionCases.reject) {
    const candidate = clonePayload();
    candidate.explanations["q-103"] = {
      translation: "يوجد تعارض غير محسوم بين المصدرين.",
      explanation: [
        "المصدر الأول يذكر Differential دون ترجيح.",
        "المصدر الثاني يذكر Incremental وتبقى المسألة للمراجعة.",
      ],
      note: `ملاحظة للمراجعة: ${selection}.`,
    };
    assert.throws(
      () => validateExplanationPayload(candidate, questions),
      /q-103 must not select an answer/i
    );
  }
});

test("q-103 selection parity fixture preserves sentence boundaries", () => {
  for (const neutralText of q103SelectionCases.allow) {
    const candidate = clonePayload();
    candidate.explanations["q-103"] = {
      translation: "يوجد تعارض غير محسوم بين المصدرين.",
      explanation: [
        "المصدر الأول يذكر Differential دون ترجيح.",
        "المصدر الثاني يذكر Incremental دون ترجيح.",
      ],
      note: `ملاحظة عربية: ${neutralText}`,
    };
    assert.doesNotThrow(() => validateExplanationPayload(candidate, questions));
  }
});

test("rejects missing and unknown explanation IDs", () => {
  const candidate = clonePayload();
  delete candidate.explanations["q-001"];
  candidate.explanations["q-999"] = structuredClone(explanations["q-002"]);

  assert.throws(
    () => validateExplanationPayload(candidate, questions),
    /missing=q-001.*unknown=q-999/i
  );
});

test("search includes Arabic translation, explanation, and note", () => {
  const result = searchExplanationEntries(questions, explanations, {
    search: "نسخ احتياطي",
  });
  assert.deepEqual(result.map((entry) => entry.question.id), ["q-007"]);

  const localQuestions = [
    { id: "q-a", prompt: "First English prompt" },
    { id: "q-b", prompt: "Second English prompt" },
  ];
  const localExplanations = {
    "q-a": {
      translation: "ترجمة أولى",
      explanation: ["شرح يتناول استعادة النظام"],
      note: "ملاحظة عامة",
    },
    "q-b": {
      translation: "ترجمة ثانية",
      explanation: ["شرح عام"],
      note: "راجع إعدادات الشبكة",
    },
  };

  assert.deepEqual(
    searchExplanationEntries(localQuestions, localExplanations, {
      search: "استعادة النظام",
    }).map((entry) => entry.question.id),
    ["q-a"]
  );
  assert.deepEqual(
    searchExplanationEntries(localQuestions, localExplanations, {
      search: "إعدادات الشبكة",
    }).map((entry) => entry.question.id),
    ["q-b"]
  );
});

test("search includes the English canonical prompt and ignores case", () => {
  const result = searchExplanationEntries(questions, explanations, {
    search: "PUBLIC KEY INFRASTRUCTURE",
  });
  assert.deepEqual(result.map((entry) => entry.question.id), ["q-003", "q-062"]);
});

test("filters entries by canonical source, topic, and type", () => {
  const selectedQuestions = questions.filter((question) =>
    ["q-003", "q-007", "q-008"].includes(question.id)
  );

  assert.deepEqual(
    searchExplanationEntries(selectedQuestions, explanations, {
      source: "pretest-70",
    }).map((entry) => entry.question.id),
    ["q-007", "q-008"]
  );
  assert.deepEqual(
    searchExplanationEntries(selectedQuestions, explanations, {
      topic: "Accounts and Permissions",
    }).map((entry) => entry.question.id),
    ["q-003", "q-008"]
  );
  assert.deepEqual(
    searchExplanationEntries(selectedQuestions, explanations, {
      type: "matching",
    }).map((entry) => entry.question.id),
    ["q-007"]
  );
});

test("missing explanations return null", () => {
  assert.equal(getExplanation({}, "q-999"), null);
  assert.equal(getExplanation(null, "q-999"), null);
});

test("existing explanations are returned unchanged", () => {
  assert.equal(getExplanation(explanations, "q-007"), explanations["q-007"]);
});
