import test from "node:test";
import assert from "node:assert/strict";
import {
  escapeHtml,
  normalizeResponse,
  renderAnswerReview,
  renderArabicExplanation,
  renderQuestion,
  scoreResponse,
} from "../js/question-renderer.js";

test("scores grouped true-false with partial detail", () => {
  const question = {
    type: "true-false-group",
    correctAnswer: [true, false, false],
  };
  assert.deepEqual(scoreResponse(question, [true, true, false]), {
    correct: false,
    earned: 2,
    possible: 3,
  });
});

test("does not credit an unanswered false statement", () => {
  const question = {
    type: "true-false-group",
    correctAnswer: [false],
  };
  assert.deepEqual(scoreResponse(question, [null]), {
    correct: false,
    earned: 0,
    possible: 1,
  });
});

test("scores matching independent of response property order", () => {
  const question = {
    type: "matching",
    correctAnswer: { a: "2", b: "1" },
  };
  assert.deepEqual(scoreResponse(question, { b: "1", a: "2" }), {
    correct: true,
    earned: 2,
    possible: 2,
  });
});

test("scores multi-select as a set", () => {
  const question = { type: "multi-select", correctAnswer: [1, 3] };
  assert.equal(scoreResponse(question, [3, 1]).correct, true);
  assert.equal(scoreResponse(question, [1, 2]).correct, false);
});

test("scores ordering by exact official order", () => {
  const question = { type: "ordering", correctAnswer: ["a", "b", "c"] };
  assert.equal(scoreResponse(question, ["a", "b", "c"]).correct, true);
  assert.equal(scoreResponse(question, ["b", "a", "c"]).correct, false);
});

test("normalizes responses by question type", () => {
  assert.equal(normalizeResponse({ type: "mcq" }, { answer: "2" }), 2);
  assert.deepEqual(
    normalizeResponse({ type: "multi-select" }, { answer: ["3", "1"] }),
    [1, 3]
  );
  assert.deepEqual(
    normalizeResponse(
      { type: "true-false-group", statements: [{}, {}] },
      { statement: ["true", "false"] }
    ),
    [true, false]
  );
});

test("rendering escapes official source text", () => {
  const html = renderQuestion({
    id: "q1",
    type: "mcq",
    prompt: '<img src=x onerror="alert(1)">',
    options: ["<script>bad()</script>", "Safe"],
    correctAnswer: 1,
    sources: [],
  });
  assert.ok(!html.includes("<script>"));
  assert.ok(!html.includes("<img"));
  assert.ok(html.includes("&lt;script&gt;"));
});

test("answer review identifies the official answer without adding explanation", () => {
  const html = renderAnswerReview(
    {
      type: "mcq",
      options: ["First", "Second"],
      correctAnswer: 1,
      explanation: "",
    },
    0
  );
  assert.ok(html.includes("Second"));
  assert.ok(!html.includes("Explanation"));
});

test("escapeHtml handles punctuation safely", () => {
  assert.equal(escapeHtml(`A&B < "C"`), "A&amp;B &lt; &quot;C&quot;");
});

test("renders semantic RTL Arabic study guidance with separate content regions", () => {
  const html = renderArabicExplanation(
    {
      type: "mcq",
      options: ["First answer", "Official answer"],
      correctAnswer: 1,
      needsReview: false,
    },
    {
      translation: "Arabic translation",
      explanation: ["Concept paragraph", "Answer reasoning paragraph"],
      note: "Revision note",
    }
  );

  assert.match(html, /<aside class="arabic-explanation" lang="ar" dir="rtl">/);
  assert.match(html, /class="explanation-guidance-label"[^>]*>[^<]*Generated study guidance/);
  assert.match(html, /class="explanation-translation"[\s\S]*Arabic translation/);
  assert.match(html, /class="explanation-official-answer"[\s\S]*Official answer/);
  assert.match(html, /class="explanation-body"[\s\S]*Concept paragraph[\s\S]*Answer reasoning paragraph/);
  assert.equal((html.match(/class="explanation-paragraph"/g) || []).length, 2);
  assert.match(html, /class="explanation-note"[\s\S]*Revision note/);
});

test("renders a source-conflict warning instead of a correct-answer region", () => {
  const html = renderArabicExplanation(
    {
      type: "source-review",
      correctAnswer: null,
      needsReview: true,
      reviewNotes: "The official sources disagree.",
    },
    {
      translation: "Conflict translation",
      explanation: ["First conflict paragraph", "Second conflict paragraph"],
      note: "Conflict note",
    }
  );

  assert.match(html, /class="explanation-conflict"/);
  assert.match(html, /Source conflict/);
  assert.match(html, /The official sources disagree\./);
  assert.doesNotMatch(html, /class="explanation-official-answer"/);
  assert.doesNotMatch(html, /Correct answer/);
});

test("renders a soft unavailable state when Arabic guidance is missing", () => {
  const html = renderArabicExplanation({ type: "mcq", correctAnswer: 0 }, null);

  assert.match(html, /<aside class="arabic-explanation" lang="ar" dir="rtl">/);
  assert.match(html, /class="explanation-unavailable"/);
  assert.match(html, /Arabic explanation is unavailable/);
});

test("escapes every rendered Arabic explanation field and the official answer", () => {
  const html = renderArabicExplanation(
    {
      type: "mcq",
      options: ["<script>official()</script>"],
      correctAnswer: 0,
      needsReview: false,
    },
    {
      translation: "<script>translation()</script>",
      explanation: [
        "<script>paragraphOne()</script>",
        "<script>paragraphTwo()</script>",
      ],
      note: "<script>note()</script>",
    }
  );

  assert.doesNotMatch(html, /<script>/);
  for (const value of [
    "official()",
    "translation()",
    "paragraphOne()",
    "paragraphTwo()",
    "note()",
  ]) {
    assert.ok(html.includes(`&lt;script&gt;${value}&lt;/script&gt;`));
  }
});

test("escapes source-conflict review notes", () => {
  const html = renderArabicExplanation(
    {
      type: "source-review",
      correctAnswer: null,
      needsReview: true,
      reviewNotes: "<script>conflict()</script>",
    },
    {
      translation: "Translation",
      explanation: ["First paragraph", "Second paragraph"],
      note: "Note",
    }
  );

  assert.doesNotMatch(html, /<script>/);
  assert.match(html, /&lt;script&gt;conflict\(\)&lt;\/script&gt;/);
});
