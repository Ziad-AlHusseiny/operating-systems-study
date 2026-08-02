import test from "node:test";
import assert from "node:assert/strict";
import {
  explanationFocusSelector,
  increaseVisibleCount,
  limitExplanationEntries,
  renderMobileMoreMenu,
} from "../js/explanations-view.js";

const elementStub = () => ({
  addEventListener() {},
  classList: { toggle() {} },
  querySelector() { return null; },
  querySelectorAll() { return []; },
  setAttribute() {},
});
const documentElements = new Map();
globalThis.document = {
  documentElement: { dataset: {} },
  querySelector(selector) {
    if (!documentElements.has(selector)) documentElements.set(selector, elementStub());
    return documentElements.get(selector);
  },
  querySelectorAll() { return []; },
};
globalThis.localStorage = {
  getItem() { return null; },
  setItem() {},
};
globalThis.window = {
  addEventListener() {},
  scrollTo() {},
};
globalThis.location = { hash: "#/dashboard" };
globalThis.matchMedia = () => ({ matches: false });
globalThis.fetch = () => new Promise(() => {});

const appModule = await import("../js/app.js");
const {
  app,
  bankMarkup,
  dashboardMarkup,
  explanationDisclosure,
  questionListMarkup,
  resultsMarkup,
  sessionMarkup,
  setupMarkup,
} = appModule;

const integrationQuestion = {
  id: "q-001",
  type: "mcq",
  topic: "Windows Basics",
  prompt: "Which answer is correct?",
  options: ["Wrong answer", "Official answer"],
  correctAnswer: 1,
  sources: [{ collection: "bank-105", page: 5 }],
};
const integrationExplanation = {
  translation: "ما الإجابة الصحيحة؟",
  explanation: ["توضح الفقرة المفهوم.", "الإجابة الرسمية هي الاختيار الثاني."],
  note: "راجع الإجابة الرسمية.",
};

function configureIntegrationState({ includeExplanation = true } = {}) {
  app.questions = [integrationQuestion];
  app.bank = { sourceEntryCount: 1 };
  app.questionMap = new Map([[integrationQuestion.id, integrationQuestion]]);
  app.explanations = includeExplanation
    ? { [integrationQuestion.id]: integrationExplanation }
    : {};
  app.state = {
    ...app.state,
    bookmarks: [],
    progress: {},
  };
}

function sessionFixture(mode) {
  return {
    mode,
    index: 0,
    questionIds: [integrationQuestion.id],
    answers: {
      [integrationQuestion.id]: {
        response: 1,
        correct: true,
        earned: 1,
        possible: 1,
      },
    },
    flagged: [],
    startedAt: 1_000,
    stats: {
      accuracy: 100,
      correct: 1,
      wrong: 0,
      skipped: 0,
      durationSeconds: 60,
    },
  };
}

const entries = Array.from({ length: 40 }, (_, index) => ({ id: index + 1 }));

test("limits the first explanation render to 15 entries by default", () => {
  assert.deepEqual(
    limitExplanationEntries(entries).map((entry) => entry.id),
    Array.from({ length: 15 }, (_, index) => index + 1)
  );
});

test("limits explanation entries to the requested visible count", () => {
  assert.deepEqual(
    limitExplanationEntries(entries, 30).map((entry) => entry.id),
    Array.from({ length: 30 }, (_, index) => index + 1)
  );
  assert.deepEqual(limitExplanationEntries(entries, 0), []);
});

test("show more increases the visible count by 15 by default", () => {
  assert.equal(increaseVisibleCount(15, 40), 30);
});

test("show more never exceeds the filtered result total", () => {
  assert.equal(increaseVisibleCount(30, 40), 40);
  assert.equal(increaseVisibleCount(15, 18, 10), 18);
});

test("mobile More uses a native menu with both secondary study routes", () => {
  const html = renderMobileMoreMenu();

  assert.match(html, /<details class="mobile-more">/);
  assert.match(html, /<summary class="mobile-nav__item">More<\/summary>/);
  assert.match(html, /href="#\/revision"[^>]*data-route="revision"/);
  assert.match(html, /href="#\/explanations"[^>]*data-route="explanations"/);
});

test("focus selectors target the changed explanation filter", () => {
  assert.equal(
    explanationFocusSelector({ filterName: "topic" }),
    '[data-explanation-filter-form] [name="topic"]'
  );
  assert.equal(
    explanationFocusSelector({ filterName: "source" }),
    '[data-explanation-filter-form] [name="source"]'
  );
});

test("focus selectors target the matching explanation bookmark", () => {
  assert.equal(
    explanationFocusSelector({ questionId: "q-042" }),
    '[data-action="bookmark"][data-id="q-042"]'
  );
  assert.equal(explanationFocusSelector({ filterName: "unknown" }), null);
});

test("Practice shows an open Arabic explanation only after an answer is checked", () => {
  configureIntegrationState();
  const unanswered = sessionFixture("practice");
  unanswered.answers = {};

  assert.doesNotMatch(sessionMarkup(unanswered), /Arabic Explanation/);
  assert.match(
    sessionMarkup(sessionFixture("practice")),
    /data-answer-feedback>[\s\S]*class="answer-review[\s\S]*<details class="explanation-disclosure" open>[\s\S]*<summary>Arabic Explanation<\/summary>/
  );
});

test("an active Exam never exposes an Arabic explanation, even after saving an answer", () => {
  configureIntegrationState();

  const html = sessionMarkup(sessionFixture("exam"));

  assert.doesNotMatch(html, /Arabic Explanation/);
  assert.doesNotMatch(html, /arabic-explanation/);
});

test("Exam Results include the explanation inside each answer-review disclosure", () => {
  configureIntegrationState();

  const html = resultsMarkup(sessionFixture("exam"));

  assert.match(
    html,
    /<details class="revision-item">[\s\S]*class="answer-review[\s\S]*<details class="explanation-disclosure">[\s\S]*Arabic Explanation[\s\S]*<\/details>[\s\S]*<\/details>/
  );
});

test("Question Bank keeps the explanation after the official answer inside its closed row", () => {
  configureIntegrationState();

  const html = questionListMarkup([integrationQuestion]);
  const outerDetails = html.indexOf('<details class="bank-row">');
  const officialAnswer = html.indexOf("<strong>Official answer:</strong>");
  const disclosure = html.indexOf('<details class="explanation-disclosure">');
  const outerClose = html.lastIndexOf("</details>");

  assert.ok(outerDetails >= 0);
  assert.doesNotMatch(html.slice(outerDetails, html.indexOf(">", outerDetails) + 1), / open(?:\s|>)/);
  assert.ok(outerDetails < officialAnswer);
  assert.ok(officialAnswer < disclosure);
  assert.ok(disclosure < outerClose);
});

test("the disclosure uses native expanded state and soft-renders missing guidance", () => {
  configureIntegrationState({ includeExplanation: false });

  assert.equal(typeof explanationDisclosure, "function");
  const html = explanationDisclosure(integrationQuestion, { open: true });

  assert.match(html, /^\s*<details class="explanation-disclosure" open>/);
  assert.match(html, /<summary>Arabic Explanation<\/summary>/);
  assert.doesNotMatch(html, /aria-expanded/);
  assert.match(html, /class="explanation-unavailable"/);
  assert.match(html, /Arabic explanation is unavailable/);
});

test("Question Bank distinguishes official PDF content from generated Arabic guidance", () => {
  configureIntegrationState();

  const html = bankMarkup();

  assert.match(html, /Questions and official answers come from the PDFs\./);
  assert.match(html, /Arabic explanations are generated study guidance and are labeled separately\./);
  assert.doesNotMatch(html, />Official PDF content only</);
});

test("Question Bank labels review items as review despite stale wrong progress", () => {
  const reviewed = {
    ...integrationQuestion,
    id: "q-reviewed-bank",
    needsReview: true,
    reviewNotes: "Review this marked key.",
  };
  app.state = {
    ...app.state,
    bookmarks: [],
    progress: {
      [reviewed.id]: { status: "wrong", attempts: 4, incorrectAttempts: 3, lastAnswer: 0 },
    },
  };

  const html = questionListMarkup([reviewed], "", { showProgress: true });

  assert.match(html, /<span class="tag tag--review">review<\/span>/);
  assert.doesNotMatch(html, /tag--wrong/);
  assert.doesNotMatch(html, /Incorrect attempts/);
});

test("Mock Exam setup states that review items are always excluded", () => {
  assert.equal(typeof setupMarkup, "function");
  const html = setupMarkup("exam");

  assert.match(html, /review items are always excluded from Mock Exams/i);
  assert.doesNotMatch(html, /name="excludeReview"/);
  assert.match(setupMarkup("practice"), /name="excludeReview"/);
});

test("Exam results label reviewed answers unscored and omit them from breakdowns", () => {
  const scored = {
    ...integrationQuestion,
    id: "q-scored",
    topic: "Scored Topic",
    sources: [{ collection: "bank-105", page: 5 }],
  };
  const reviewedShared = {
    ...integrationQuestion,
    id: "q-reviewed-shared",
    prompt: "Shared reviewed prompt",
    topic: "Scored Topic",
    needsReview: true,
    reviewNotes: "Marked key requires review.",
    sources: [{ collection: "bank-105", page: 6 }],
  };
  const reviewedOnly = {
    ...integrationQuestion,
    id: "q-reviewed-only",
    prompt: "Only reviewed prompt",
    topic: "Reviewed Topic",
    needsReview: true,
    reviewNotes: "Marked key requires review.",
    sources: [{ collection: "pretest-70", page: 21 }],
  };
  app.questions = [scored, reviewedShared, reviewedOnly];
  app.questionMap = new Map(app.questions.map((question) => [question.id, question]));
  app.explanations = {
    [scored.id]: integrationExplanation,
    [reviewedShared.id]: integrationExplanation,
    [reviewedOnly.id]: integrationExplanation,
  };

  const html = resultsMarkup({
    mode: "exam",
    questionIds: [scored.id, reviewedShared.id, reviewedOnly.id],
    answers: {
      [scored.id]: { response: 1, correct: true, earned: 1, possible: 1 },
      [reviewedShared.id]: { response: 1, correct: null, earned: 0, possible: 0 },
      [reviewedOnly.id]: { response: 1, correct: null, earned: 0, possible: 0 },
    },
    stats: { accuracy: 100, correct: 1, wrong: 0, skipped: 2, durationSeconds: 60 },
  });

  assert.match(html, /Shared reviewed prompt[\s\S]*<span class="tag">Unscored<\/span>/);
  assert.match(html, /Only reviewed prompt[\s\S]*<span class="tag">Unscored<\/span>/);
  assert.doesNotMatch(html, /reviewed prompt<\/span><span class="tag">Wrong<\/span>/i);
  assert.doesNotMatch(html, /<strong>Reviewed Topic<\/strong>/);
  assert.doesNotMatch(html, /70 Question Pre-Test/);
  assert.match(html, /<strong>Scored Topic<\/strong>[\s\S]*1\/1 correct/);
  assert.match(html, /<strong>105 Question Bank<\/strong>[\s\S]*1\/1 correct/);
});

test("Dashboard shows 103 unique questions with a 98-question scoring denominator", () => {
  assert.equal(typeof dashboardMarkup, "function");
  app.questions = Array.from({ length: 103 }, (_, index) => ({
    id: `q-${String(index + 1).padStart(3, "0")}`,
    topic: "Topic",
    needsReview: index >= 98,
    sources: [{ collection: "bank-105", page: index + 1 }],
  }));
  app.bank = { sourceEntryCount: 175 };
  app.state = {
    ...app.state,
    progress: {},
    bookmarks: [],
    sessions: [],
    exams: [],
    activePractice: null,
    activeExam: null,
  };

  const html = dashboardMarkup();

  assert.match(
    html,
    /Unique questions<\/span><strong class="metric-strip__value metric-value--primary">103<\/strong>/
  );
  assert.match(html, /0 of 98 scoreable questions answered\./);
  assert.doesNotMatch(html, /0 of 98 unique questions answered\./);
});
