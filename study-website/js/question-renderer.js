const LETTERS = "ABCDEFGHIJKLMNOPQRSTUVWXYZ";

export function escapeHtml(value = "") {
  return String(value)
    .replaceAll("â€¢", "•")
    .replaceAll("â€”", "—")
    .replaceAll("â€“", "–")
    .replaceAll("â€™", "’")
    .replaceAll("â€œ", "“")
    .replaceAll("â€", "”")
    .replaceAll("&", "&amp;")
    .replaceAll("<", "&lt;")
    .replaceAll(">", "&gt;")
    .replaceAll('"', "&quot;")
    .replaceAll("'", "&#039;");
}

function valuesFrom(input, name) {
  if (typeof FormData !== "undefined" && input instanceof FormData) {
    return input.getAll(name);
  }
  const value = input?.[name];
  return Array.isArray(value) ? value : value === undefined ? [] : [value];
}

export function normalizeResponse(question, input = {}) {
  switch (question.type) {
    case "mcq": {
      const value = valuesFrom(input, "answer")[0];
      return value === undefined || value === "" ? null : Number(value);
    }
    case "multi-select":
      return valuesFrom(input, "answer")
        .map(Number)
        .filter(Number.isInteger)
        .sort((a, b) => a - b);
    case "true-false-group":
      if (typeof FormData !== "undefined" && input instanceof FormData) {
        return (question.statements || []).map((_, index) => {
          const value = input.get(`statement-${index}`);
          return value === null ? null : value === "true";
        });
      }
      return valuesFrom(input, "statement")
        .slice(0, question.statements?.length || Infinity)
        .map((value) => value === true || value === "true");
    case "matching": {
      const result = {};
      for (const item of question.items || []) {
        const value = valuesFrom(input, item.id)[0];
        if (value !== undefined && value !== "") result[item.id] = String(value);
      }
      return result;
    }
    case "ordering":
      return valuesFrom(input, "order").map(String);
    case "source-review": {
      const value = valuesFrom(input, "answer")[0];
      if (value === undefined || value === "") return null;
      return value === true || value === "true" || value === "correct";
    }
    default:
      return input?.answer ?? null;
  }
}

function arraysEqual(left = [], right = []) {
  return left.length === right.length && left.every((value, index) => value === right[index]);
}

export function scoreResponse(question, response) {
  const correctAnswer = question.correctAnswer;

  if (question.needsReview) {
    return { correct: null, earned: 0, possible: 0 };
  }

  if (question.type === "source-review") {
    if (correctAnswer === null || correctAnswer === undefined) {
      return { correct: null, earned: 0, possible: 0 };
    }
    const correct = response === true;
    return { correct, earned: correct ? 1 : 0, possible: 1 };
  }

  if (question.type === "true-false-group") {
    const possible = correctAnswer?.length || 0;
    const earned = (correctAnswer || []).reduce(
      (total, answer, index) => total + (response?.[index] === answer ? 1 : 0),
      0
    );
    return { correct: possible > 0 && earned === possible, earned, possible };
  }

  if (question.type === "matching") {
    const entries = Object.entries(correctAnswer || {});
    const earned = entries.reduce(
      (total, [itemId, answer]) => total + (response?.[itemId] === answer ? 1 : 0),
      0
    );
    return { correct: entries.length > 0 && earned === entries.length, earned, possible: entries.length };
  }

  if (question.type === "multi-select") {
    const expected = [...(correctAnswer || [])].sort((a, b) => a - b);
    const received = [...(response || [])].sort((a, b) => a - b);
    const correct = arraysEqual(received, expected);
    return { correct, earned: correct ? 1 : 0, possible: 1 };
  }

  if (question.type === "ordering") {
    const correct = arraysEqual(response || [], correctAnswer || []);
    return { correct, earned: correct ? 1 : 0, possible: 1 };
  }

  const correct = response === correctAnswer;
  return { correct, earned: correct ? 1 : 0, possible: 1 };
}

function sourceNote(question) {
  const refs = (question.sources || [])
    .map((source) => `${source.collection === "bank-105" ? "105 Question Bank" : "70 Question Pre-Test"}, page ${source.page}`)
    .join(" • ");
  return refs ? `<p class="source-reference">${escapeHtml(refs)}</p>` : "";
}

function renderChoice(question, option, index, multiple = false) {
  const inputType = multiple ? "checkbox" : "radio";
  return `
    <label class="answer-option">
      <input type="${inputType}" name="answer" value="${index}">
      <span class="option-letter">${LETTERS[index] || index + 1}</span>
      <span>${escapeHtml(option)}</span>
    </label>`;
}

function renderTrueFalse(question) {
  return `
    <div class="statement-list">
      ${(question.statements || [])
        .map(
          (statement, index) => `
          <fieldset class="statement-row">
            <legend>${escapeHtml(statement)}</legend>
            <label><input type="radio" name="statement-${index}" value="true"> True</label>
            <label><input type="radio" name="statement-${index}" value="false"> False</label>
          </fieldset>`
        )
        .join("")}
    </div>`;
}

function renderMatching(question) {
  return `
    <div class="matching-list">
      ${(question.items || [])
        .map(
          (item) => `
          <label class="matching-row">
            <span>${escapeHtml(item.text)}</span>
            <select name="${escapeHtml(item.id)}">
              <option value="">Select an answer</option>
              ${(question.options || [])
                .map((option) => `<option value="${escapeHtml(option)}">${escapeHtml(option)}</option>`)
                .join("")}
            </select>
          </label>`
        )
        .join("")}
    </div>`;
}

function renderOrdering(question) {
  return `
    <p class="question-instruction">Arrange the items in the official order.</p>
    <ol class="ordering-list" data-ordering-list>
      ${(question.items || [])
        .map(
          (item, index) => `
          <li class="ordering-row">
            <input type="hidden" name="order" value="${escapeHtml(item)}">
            <span>${escapeHtml(item)}</span>
            <span class="ordering-controls">
              <button type="button" data-move="up" aria-label="Move up" ${index === 0 ? "disabled" : ""}>↑</button>
              <button type="button" data-move="down" aria-label="Move down" ${index === question.items.length - 1 ? "disabled" : ""}>↓</button>
            </span>
          </li>`
        )
        .join("")}
    </ol>`;
}

function renderSourceReview(question) {
  const unresolved = question.correctAnswer === null || question.correctAnswer === undefined;
  return `
    ${question.sourceImage ? `<img class="source-question-image" src="${escapeHtml(question.sourceImage)}" alt="Original source question">` : ""}
    ${
      unresolved
        ? `<div class="review-warning">The two official PDFs show different answers. This item is preserved for source review and is not scored.</div>`
        : `<p class="question-instruction">Review the source image, then reveal the official answer.</p>
           <label class="answer-option"><input type="radio" name="answer" value="true"><span>I matched the official answer</span></label>
           <label class="answer-option"><input type="radio" name="answer" value="false"><span>I did not match the official answer</span></label>`
    }`;
}

export function renderQuestion(question, context = {}) {
  let answerArea = "";
  if (question.type === "mcq" || question.type === "multi-select") {
    answerArea = `<div class="answer-list">${(question.options || [])
      .map((option, index) => renderChoice(question, option, index, question.type === "multi-select"))
      .join("")}</div>`;
  } else if (question.type === "true-false-group") {
    answerArea = renderTrueFalse(question);
  } else if (question.type === "matching") {
    answerArea = renderMatching(question);
  } else if (question.type === "ordering") {
    answerArea = renderOrdering(question);
  } else if (question.type === "source-review") {
    answerArea = renderSourceReview(question);
  }

  return `
    <article class="question-card" data-question-id="${escapeHtml(question.id)}">
      <header class="question-card-header">
        <span class="question-type">${escapeHtml(question.type.replaceAll("-", " "))}</span>
        <span class="question-topic">${escapeHtml(question.topic || "General")}</span>
      </header>
      <h2 class="question-prompt">${escapeHtml(question.prompt)}</h2>
      ${context.showSource === false ? "" : sourceNote(question)}
      <form class="question-form" data-question-form>
        ${answerArea}
      </form>
    </article>`;
}

function describeAnswer(question, answer) {
  if (answer === null || answer === undefined) return "No agreed official answer";
  if (question.type === "mcq") return question.options?.[answer] ?? String(answer);
  if (question.type === "multi-select") return answer.map((index) => question.options?.[index] ?? index).join("; ");
  if (question.type === "true-false-group") {
    return (question.statements || [])
      .map((statement, index) => `${statement}: ${answer[index] ? "True" : "False"}`)
      .join("; ");
  }
  if (question.type === "matching") {
    return (question.items || []).map((item) => `${item.text}: ${answer[item.id]}`).join("; ");
  }
  if (question.type === "ordering") return answer.join(" → ");
  return String(answer);
}

export function renderArabicExplanation(question, explanation, options = {}) {
  const guidanceLabel =
    options.generatedStudyGuidance === false
      ? ""
      : `<p class="explanation-guidance-label">${escapeHtml("Generated study guidance — not an official source explanation")}</p>`;

  if (!explanation) {
    return `
      <aside class="arabic-explanation" lang="ar" dir="rtl">
        <p class="explanation-unavailable">${escapeHtml("Arabic explanation is unavailable for this question.")}</p>
      </aside>`;
  }

  const answerRegion = question.needsReview
    ? `<section class="explanation-conflict" role="alert">
         <h3>${escapeHtml("Answer review warning")}</h3>
         <p>${escapeHtml(question.reviewNotes || "The marked source answer requires review, so no correct answer is shown.")}</p>
       </section>`
    : `<section class="explanation-official-answer">
         <h3>${escapeHtml("Official answer")}</h3>
         <p>${escapeHtml(describeAnswer(question, question.correctAnswer))}</p>
       </section>`;

  return `
    <aside class="arabic-explanation" lang="ar" dir="rtl">
      ${guidanceLabel}
      <section class="explanation-translation">
        <h3>${escapeHtml("Arabic translation")}</h3>
        <p>${escapeHtml(explanation.translation)}</p>
      </section>
      ${answerRegion}
      <section class="explanation-body">
        <h3>${escapeHtml("Explanation")}</h3>
        ${(explanation.explanation || [])
          .map((paragraph) => `<p class="explanation-paragraph">${escapeHtml(paragraph)}</p>`)
          .join("")}
      </section>
      <section class="explanation-note">
        <h3>${escapeHtml("Revision note")}</h3>
        <p>${escapeHtml(explanation.note)}</p>
      </section>
    </aside>`;
}

export function renderAnswerReview(question, response) {
  const result = scoreResponse(question, response);
  const official = describeAnswer(question, question.correctAnswer);
  const answerLabel =
    question.needsReview && question.correctAnswer !== null && question.correctAnswer !== undefined
      ? "Marked source answer"
      : "Official answer";
  const selected =
    question.type === "source-review"
      ? response === null
        ? "Not answered"
        : response
          ? "Matched"
          : "Did not match"
      : describeAnswer(question, response);
  const status =
    result.correct === null ? "Answer review warning" : result.correct ? "Correct" : "Review this answer";

  return `
    <section class="answer-review ${result.correct === true ? "is-correct" : result.correct === false ? "is-incorrect" : "is-unscored"}">
      <h3>${status}</h3>
      <p><strong>Your answer:</strong> ${escapeHtml(selected)}</p>
      <p><strong>${escapeHtml(answerLabel)}:</strong> ${escapeHtml(official)}</p>
      ${
        result.possible > 1
          ? `<p><strong>Credit:</strong> ${result.earned} of ${result.possible}</p>`
          : ""
      }
      ${
        question.explanation
          ? `<div class="source-explanation"><strong>Source explanation:</strong> ${escapeHtml(question.explanation)}</div>`
          : ""
      }
      ${
        question.reviewNotes
          ? `<div class="review-warning">${escapeHtml(question.reviewNotes)}</div>`
          : ""
      }
    </section>`;
}
