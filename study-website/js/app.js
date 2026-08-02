import { filterQuestions, loadQuestionBank, shuffleChoices } from "./questions.js";
import {
  loadExplanations,
  searchExplanationEntries,
  validateExplanationPayload,
} from "./explanations.js";
import {
  increaseVisibleCount,
  limitExplanationEntries,
} from "./explanations-view.js";
import {
  escapeHtml,
  normalizeResponse,
  renderAnswerReview,
  renderArabicExplanation,
  renderQuestion,
} from "./question-renderer.js";
import {
  answerSessionQuestion,
  createSession,
  finishSession,
  getRemainingSeconds,
  goToSessionQuestion,
  moveSession,
  toggleSessionFlag,
} from "./quiz.js";
import { buildRevisionSummary } from "./revision.js";
import {
  exportState,
  importState,
  loadState,
  recordAttempt,
  resetState,
  saveState,
  toggleBookmark,
} from "./storage.js";
import { getDashboardStats } from "./statistics.js";

const main = document.querySelector("#main-content");
const appShell = document.querySelector("#app-shell");
const themeToggle = document.querySelector("#theme-toggle");
const themeLabel = document.querySelector("#theme-toggle-label");
const sidebarCollapse = document.querySelector("#sidebar-collapse");
const fileInput = document.querySelector("#progress-file-input");
const toastRegion = document.querySelector("#toast-region");

const app = {
  bank: null,
  questions: [],
  questionMap: new Map(),
  explanations: {},
  explanationPayload: null,
  explanationsError: null,
  state: loadState(),
  finishedSession: null,
  filters: { search: "", source: "all", type: "all", topic: "all", status: "all", focus: "all" },
  revisionFilters: { source: "all", topic: "all" },
  explanationFilters: { search: "", source: "all", type: "all", topic: "all" },
  visibleExplanationCount: 15,
  timer: null,
};

function icon(name) {
  const paths = {
    play: '<path d="m8 5 11 7-11 7Z"/>',
    exam: '<path d="M6 3h9l4 4v14H6Z"/><path d="M14 3v5h5M9 13h6M9 17h6"/>',
    mistakes: '<circle cx="12" cy="12" r="9"/><path d="m9 9 6 6m0-6-6 6"/>',
    bookmark: '<path d="M6 3h12v18l-6-4-6 4Z"/>',
    inbox: '<path d="M4 5h16l2 10v4H2v-4Z"/><path d="M2 15h6l2 2h4l2-2h6"/>',
    download: '<path d="M12 3v12m0 0 5-5m-5 5-5-5M4 20h16"/>',
    upload: '<path d="M12 17V5m0 0 5 5m-5-5-5 5M4 20h16"/>',
  };
  return `<svg aria-hidden="true" viewBox="0 0 24 24">${paths[name] || ""}</svg>`;
}

function toast(message, error = false) {
  const item = document.createElement("div");
  item.className = `toast${error ? " toast--error" : ""}`;
  item.textContent = message;
  toastRegion.append(item);
  setTimeout(() => item.remove(), 3500);
}

function persist(nextState = app.state) {
  app.state = saveState(nextState);
}

function currentRoute() {
  return location.hash.replace(/^#\//, "").split("/")[0] || "dashboard";
}

function heading(title, copy = "", actions = "") {
  return `<header class="page-header"><div><h1>${escapeHtml(title)}</h1>${
    copy ? `<p>${escapeHtml(copy)}</p>` : ""
  }</div>${actions ? `<div class="page-actions">${actions}</div>` : ""}</header>`;
}

function sourceLabel(source) {
  return source.collection === "bank-105" ? "105 Question Bank" : "70 Question Pre-Test";
}

function formatDuration(seconds = 0) {
  const minutes = Math.floor(seconds / 60);
  const remaining = Math.round(seconds % 60);
  return `${minutes}:${String(remaining).padStart(2, "0")}`;
}

function dashboardMarkup() {
  const stats = getDashboardStats(app.questions, app.state);
  const recent = [...app.state.sessions, ...app.state.exams]
    .sort((a, b) => (b.finishedAt || 0) - (a.finishedAt || 0))
    .slice(0, 5);
  const summary = buildRevisionSummary(app.questions, app.state);
  return `
    ${heading("Dashboard", "Study all official material from both PDF collections.")}
    <section class="progress-panel" aria-label="Overall progress">
      <div class="progress-panel__main">
        <div class="progress-panel__section">
          <div class="metric-label">Completion</div>
          <div class="metric-value metric-value--primary">${stats.completion}%</div>
          <div class="progress-track" aria-label="${stats.completion}% complete">
            <div class="progress-track__fill" style="--progress: ${stats.completion}%"></div>
          </div>
          <p class="metric-help">${stats.answered} of ${stats.total} unique questions answered.</p>
        </div>
        <div class="progress-panel__section">
          <div class="metric-label">Accuracy</div>
          <div class="metric-value">${stats.answered ? `${stats.accuracy}%` : "—"}</div>
          <p class="metric-help">${stats.answered ? "Based only on answered questions." : "Complete questions to see your accuracy."}</p>
        </div>
      </div>
      <div class="metric-strip">
        <div class="metric-strip__item"><span class="metric-label">Unique questions</span><strong class="metric-strip__value metric-value--primary">${stats.total}</strong></div>
        <div class="metric-strip__item"><span class="metric-label">Source entries</span><strong class="metric-strip__value">${app.bank.sourceEntryCount}</strong></div>
        <div class="metric-strip__item"><span class="metric-label">Answered</span><strong class="metric-strip__value">${stats.answered}</strong></div>
        <div class="metric-strip__item"><span class="metric-label">Correct</span><strong class="metric-strip__value metric-value--success">${stats.correct}</strong></div>
        <div class="metric-strip__item"><span class="metric-label">Wrong</span><strong class="metric-strip__value metric-value--danger">${stats.wrong}</strong></div>
      </div>
    </section>
    <div class="dashboard-actions">
      <a class="btn btn--primary" href="#/practice">${icon("play")}Start Practice</a>
      <a class="btn btn--primary" href="#/exam">${icon("exam")}Start Mock Exam</a>
      ${app.state.activePractice ? `<button class="btn btn--secondary" data-action="continue-practice">Continue Practice</button>` : ""}
      ${app.state.activeExam ? `<button class="btn btn--secondary" data-action="continue-exam">Continue Exam</button>` : ""}
      <a class="btn btn--secondary" href="#/mistakes">${icon("mistakes")}Review Mistakes</a>
      <a class="btn btn--secondary" href="#/bookmarks">${icon("bookmark")}Review Bookmarks</a>
    </div>
    <section class="section-block">
      <div class="section-header"><h2>Recent Activity</h2></div>
      ${
        recent.length
          ? `<div class="breakdown-list">${recent
              .map(
                (session) => `<div class="breakdown-row"><span><strong>${session.mode === "exam" ? "Mock Exam" : "Practice"}</strong><small>${new Date(session.finishedAt).toLocaleString()}</small></span><strong>${session.stats?.accuracy || 0}%</strong></div>`
              )
              .join("")}</div>`
          : `<div class="empty-state">${icon("inbox")}<strong>No recent activity yet.</strong><p>Start practicing to see your sessions here.</p></div>`
      }
    </section>
    <section class="section-block">
      <div class="section-header"><h2>Revision Summary</h2><a class="btn btn--quiet" href="#/revision">Open summary</a></div>
      <div class="revision-cards">
        <div class="mini-card"><span>Current mistakes</span><strong>${summary.mistakes.length}</strong></div>
        <div class="mini-card"><span>Bookmarks</span><strong>${summary.bookmarks.length}</strong></div>
        <div class="mini-card"><span>Weak topics</span><strong>${summary.weakTopics.length}</strong></div>
      </div>
    </section>
    <section class="section-block">
      <div class="section-header"><h2>Progress Data</h2></div>
      <div class="page-actions">
        <button class="btn btn--secondary" data-action="export">${icon("download")}Export</button>
        <button class="btn btn--secondary" data-action="import">${icon("upload")}Import</button>
        <button class="btn btn--danger" data-action="reset">Reset progress</button>
      </div>
    </section>`;
}

function setupMarkup(mode) {
  const isExam = mode === "exam";
  const topics = [...new Set(app.questions.map((question) => question.topic))].sort();
  const types = [...new Set(app.questions.map((question) => question.type))].sort();
  return `
    ${heading(isExam ? "Mock Exam" : "Practice", isExam ? "Answer first, then review your complete result." : "Get immediate official-answer feedback after every question.")}
    <section class="section-block setup-card">
      <form data-setup-form data-mode="${mode}">
        <div class="form-grid">
          <label class="field"><span>Questions</span><select class="select" name="count">
            ${[10, 20, 30, 50, app.questions.length].map((count) => `<option value="${count}">${count === app.questions.length ? `All ${count}` : count}</option>`).join("")}
          </select></label>
          <label class="field"><span>Source</span><select class="select" name="source">
            <option value="all">Both PDF collections</option>
            <option value="bank-105">105 Question Bank</option>
            <option value="pretest-70">70 Question Pre-Test</option>
          </select></label>
          <label class="field"><span>Topic</span><select class="select" name="topic">
            <option value="all">All topics</option>
            ${topics.map((topic) => `<option value="${escapeHtml(topic)}">${escapeHtml(topic)}</option>`).join("")}
          </select></label>
          <label class="field"><span>Question type</span><select class="select" name="type">
            <option value="all">All types</option>
            ${types.map((type) => `<option value="${type}">${escapeHtml(type.replaceAll("-", " "))}</option>`).join("")}
          </select></label>
          ${
            !isExam
              ? `<label class="field"><span>Progress</span><select class="select" name="status">
                  <option value="all">All questions</option>
                  <option value="unanswered">Unanswered only</option>
                  <option value="wrong">Current mistakes</option>
                  <option value="bookmarked">Bookmarks only</option>
                </select></label>`
              : ""
          }
          ${
            isExam
              ? `<label class="field"><span>Time limit</span><select class="select" name="durationMinutes">
                  <option value="0">Untimed</option><option value="20">20 minutes</option><option value="45">45 minutes</option><option value="60">60 minutes</option>
                </select></label>`
              : ""
          }
        </div>
        <label class="checkbox-row"><input type="checkbox" name="shuffle" checked> Shuffle question order</label>
        ${!isExam ? `<label class="checkbox-row"><input type="checkbox" name="shuffleChoices"> Shuffle choices for single and multiple choice questions</label>` : ""}
        <label class="checkbox-row"><input type="checkbox" name="excludeReview" ${isExam ? "checked" : ""}> Exclude the one unresolved source-conflict item</label>
        <button class="btn btn--primary" type="submit">${isExam ? "Start Mock Exam" : "Start Practice"}</button>
      </form>
    </section>`;
}

function questionForSession(session, id) {
  return session.questionOverrides?.[id] || app.questionMap.get(id);
}

function responseFromForm(question, form) {
  const data = new FormData(form);
  if (question.type === "true-false-group") {
    return (question.statements || []).map((_, index) => {
      const value = data.get(`statement-${index}`);
      return value === null ? null : value === "true";
    });
  }
  return normalizeResponse(question, data);
}

function applySavedResponse(question, response) {
  if (response === null || response === undefined) return;
  const form = main.querySelector("[data-question-form]");
  if (!form) return;
  if (question.type === "mcq" || question.type === "source-review") {
    const control = form.querySelector(`[name="answer"][value="${response}"]`);
    if (control) control.checked = true;
  } else if (question.type === "multi-select") {
    for (const value of response) {
      const control = form.querySelector(`[name="answer"][value="${value}"]`);
      if (control) control.checked = true;
    }
  } else if (question.type === "true-false-group") {
    response.forEach((value, index) => {
      const control = form.querySelector(`[name="statement-${index}"][value="${value}"]`);
      if (control) control.checked = true;
    });
  } else if (question.type === "matching") {
    for (const [name, value] of Object.entries(response)) {
      const control = form.elements.namedItem(name);
      if (control) control.value = value;
    }
  }
}

function sessionMarkup(session) {
  if (!session.questionIds.length) {
    return `${heading("No matching questions")}<div class="empty-state"><strong>Change the filters and try again.</strong><a class="btn btn--primary" href="#/${session.mode}">Back to setup</a></div>`;
  }
  const question = questionForSession(session, session.questionIds[session.index]);
  const saved = session.answers[question.id];
  const isExam = session.mode === "exam";
  const remaining = getRemainingSeconds(session);
  return `
    ${heading(isExam ? "Mock Exam" : "Practice", `${session.index + 1} of ${session.questionIds.length}`, isExam && remaining !== null ? `<strong class="timer" data-timer>${formatDuration(remaining)}</strong>` : "")}
    <div class="question-layout">
      <section class="question-workspace">
        <div class="question-progress"><div class="progress-track"><div class="progress-track__fill" style="--progress:${Math.round(((session.index + 1) / session.questionIds.length) * 100)}%"></div></div></div>
        ${renderQuestion(question)}
        <div data-answer-feedback>${!isExam && saved ? renderAnswerReview(question, saved.response) : ""}</div>
        <footer class="question-footer">
          <div class="question-footer__group">
            <button class="btn btn--secondary" data-action="previous" ${session.index === 0 ? "disabled" : ""}>Previous</button>
            <button class="btn btn--quiet" data-action="flag">${session.flagged?.includes(question.id) ? "Remove flag" : "Flag for review"}</button>
            <button class="btn btn--quiet bookmark-toggle" data-action="bookmark" data-id="${question.id}">${app.state.bookmarks.includes(question.id) ? "★ Bookmarked" : "☆ Bookmark"}</button>
          </div>
          <div class="question-footer__group">
            ${!saved || isExam ? `<button class="btn btn--primary" data-action="submit-answer">${isExam ? "Save Answer" : "Check Answer"}</button>` : ""}
            <button class="btn btn--secondary" data-action="next">${session.index === session.questionIds.length - 1 ? "Finish" : "Next"}</button>
          </div>
        </footer>
      </section>
      <aside class="session-rail">
        <h2>Questions</h2>
        <div class="navigator-grid">
          ${session.questionIds.map((id, index) => `<button class="navigator-button${index === session.index ? " is-current" : ""}${session.answers[id] ? " is-answered" : ""}" data-action="goto" data-index="${index}">${index + 1}</button>`).join("")}
        </div>
        <div class="session-stat"><span class="session-stat__label">Answered</span><strong>${Object.keys(session.answers).length}/${session.questionIds.length}</strong></div>
        ${session.flagged?.length ? `<div class="session-stat"><span class="session-stat__label">Flagged</span><strong>${session.flagged.length}</strong></div>` : ""}
        <button class="btn btn--danger" data-action="finish-session">Finish ${isExam ? "Exam" : "Practice"}</button>
      </aside>
    </div>`;
}

function resultsMarkup(session) {
  const { stats } = session;
  const topicRows = sessionBreakdown(session, "topic");
  const sourceRows = sessionBreakdown(session, "source");
  const wrongIds = session.questionIds.filter((id) => session.answers[id]?.correct === false);
  return `
    ${heading(session.mode === "exam" ? "Exam Result" : "Practice Result", "Your progress has been saved in this browser.")}
    <section class="results-summary">
      <div class="score-circle"><strong>${stats.accuracy}%</strong><span>accuracy</span></div>
      <div class="revision-cards">
        <div class="mini-card"><span>Correct</span><strong class="metric-value--success">${stats.correct}</strong></div>
        <div class="mini-card"><span>Wrong</span><strong class="metric-value--danger">${stats.wrong}</strong></div>
        <div class="mini-card"><span>Skipped</span><strong>${stats.skipped}</strong></div>
        <div class="mini-card"><span>Time</span><strong>${formatDuration(stats.durationSeconds)}</strong></div>
      </div>
    </section>
    <div class="page-actions">
      <a class="btn btn--primary" href="#/${session.mode}">Start another</a>
      ${wrongIds.length ? `<button class="btn btn--secondary" data-action="retry-wrong" data-ids="${wrongIds.join(",")}">Retry wrong questions</button>` : ""}
      <a class="btn btn--secondary" href="#/mistakes">Review mistakes</a>
    </div>
    <section class="section-block">
      <div class="section-header"><h2>Performance Breakdown</h2></div>
      <div class="results-breakdowns">
        <div><h3>By topic</h3>${breakdownRows(topicRows)}</div>
        <div><h3>By source</h3>${breakdownRows(sourceRows)}</div>
      </div>
    </section>
    <section class="section-block"><div class="section-header"><h2>Answer Review</h2></div>
      <div class="revision-list">${session.questionIds.map((id, index) => {
        const question = questionForSession(session, id);
        const answer = session.answers[id];
        return `<details class="revision-item"><summary><span>${index + 1}. ${escapeHtml(question.prompt)}</span><span class="tag">${answer ? (answer.correct ? "Correct" : "Wrong") : "Skipped"}</span></summary>${renderAnswerReview(question, answer?.response ?? null)}</details>`;
      }).join("")}</div>
    </section>`;
}

function sessionBreakdown(session, dimension) {
  const groups = new Map();
  for (const id of session.questionIds) {
    const question = questionForSession(session, id);
    const names =
      dimension === "source"
        ? [...new Set(question.sources.map((source) => sourceLabel(source)))]
        : [question.topic || "General"];
    for (const name of names) {
      const group = groups.get(name) || { name, correct: 0, answered: 0 };
      const answer = session.answers[id];
      if (answer) {
        group.answered += 1;
        if (answer.correct) group.correct += 1;
      }
      groups.set(name, group);
    }
  }
  return [...groups.values()]
    .map((group) => ({
      ...group,
      accuracy: group.answered ? Math.round((group.correct / group.answered) * 100) : 0,
    }))
    .sort((left, right) => left.accuracy - right.accuracy || left.name.localeCompare(right.name));
}

function breakdownRows(rows) {
  return `<div class="breakdown-list">${rows
    .map(
      (row) =>
        `<div class="breakdown-row"><span><strong>${escapeHtml(row.name)}</strong><small>${row.correct}/${row.answered} correct</small></span><strong>${row.accuracy}%</strong></div>`
    )
    .join("")}</div>`;
}

function bankFiltersMarkup() {
  const topics = [...new Set(app.questions.map((question) => question.topic))].sort();
  const types = [...new Set(app.questions.map((question) => question.type))].sort();
  return `<form class="filter-bar" data-filter-form>
    <label class="field"><span>Search</span><input class="input" name="search" value="${escapeHtml(app.filters.search)}" placeholder="Search questions and topics"></label>
    <label class="field"><span>Source</span><select class="select" name="source">
      <option value="all">Both sources</option><option value="bank-105" ${app.filters.source === "bank-105" ? "selected" : ""}>105 Question Bank</option><option value="pretest-70" ${app.filters.source === "pretest-70" ? "selected" : ""}>70 Question Pre-Test</option>
    </select></label>
    <label class="field"><span>Type</span><select class="select" name="type"><option value="all">All types</option>${types.map((type) => `<option value="${type}" ${app.filters.type === type ? "selected" : ""}>${escapeHtml(type)}</option>`).join("")}</select></label>
    <label class="field"><span>Topic</span><select class="select" name="topic"><option value="all">All topics</option>${topics.map((topic) => `<option value="${escapeHtml(topic)}" ${app.filters.topic === topic ? "selected" : ""}>${escapeHtml(topic)}</option>`).join("")}</select></label>
    <label class="field"><span>Status</span><select class="select" name="status"><option value="all">Any status</option><option value="unanswered" ${app.filters.status === "unanswered" ? "selected" : ""}>Unanswered</option><option value="correct" ${app.filters.status === "correct" ? "selected" : ""}>Correct</option><option value="wrong" ${app.filters.status === "wrong" ? "selected" : ""}>Wrong</option></select></label>
    <label class="field"><span>Saved / review</span><select class="select" name="focus">
      <option value="all">All questions</option>
      <option value="bookmarked" ${app.filters.focus === "bookmarked" ? "selected" : ""}>Bookmarked only</option>
      <option value="review" ${app.filters.focus === "review" ? "selected" : ""}>Manual review only</option>
    </select></label>
  </form>`;
}

function questionListMarkup(
  questions,
  emptyCopy = "No questions match these filters.",
  { showProgress = false } = {}
) {
  if (!questions.length) return `<div class="empty-state"><strong>${escapeHtml(emptyCopy)}</strong></div>`;
  return `<div class="bank-list">${questions.map((question) => {
    const status = app.state.progress[question.id]?.status || "unanswered";
    const progress = app.state.progress[question.id];
    const sourceRefs = question.sources.map((source) => `${sourceLabel(source)} p.${source.page}`).join(" • ");
    return `<details class="bank-row">
      <summary>
        <span class="bank-row__number">${question.id.replace("q-", "")}</span>
        <span class="bank-row__prompt">${escapeHtml(question.prompt)}<small class="bank-row__meta">${escapeHtml(question.topic)} • ${escapeHtml(sourceRefs)}</small></span>
        <span class="tag tag--${status}">${status}</span>
      </summary>
      <div class="bank-row__details">
        ${renderQuestion(question)}
        ${renderAnswerReview(question, showProgress && progress ? progress.lastAnswer : null)}
        ${
          showProgress && progress
            ? `<p class="attempt-note"><strong>Attempts:</strong> ${progress.attempts} • <strong>Incorrect attempts:</strong> ${progress.incorrectAttempts}</p>`
            : ""
        }
        <button class="btn btn--secondary" data-action="bookmark" data-id="${question.id}">${app.state.bookmarks.includes(question.id) ? "★ Remove bookmark" : "☆ Bookmark"}</button>
      </div>
    </details>`;
  }).join("")}</div>`;
}

function bankMarkup() {
  const filtered = filterQuestions(app.questions, {
    ...app.filters,
    bookmarked: app.filters.focus === "bookmarked",
    needsReview: app.filters.focus === "review" ? true : undefined,
    bookmarks: app.state.bookmarks,
    progress: app.state.progress,
  });
  return `${heading("Question Bank", `Browse ${app.questions.length} unique questions covering all ${app.bank.sourceEntryCount} source entries.`)}
    ${bankFiltersMarkup()}
    <section class="section-block section-block--flat"><div class="section-header"><h2>${filtered.length} questions</h2><span>Official PDF content only</span></div>${questionListMarkup(filtered)}</section>`;
}

function explanationFiltersMarkup() {
  const topics = [...new Set(app.questions.map((question) => question.topic))].sort();
  const types = [...new Set(app.questions.map((question) => question.type))].sort();
  return `<form class="filter-bar explanation-filter-bar" data-explanation-filter-form>
    <label class="field"><span>Search English or Arabic</span><input class="input" name="search" value="${escapeHtml(app.explanationFilters.search)}" placeholder="Search questions or Arabic guidance" autocomplete="off"></label>
    <label class="field"><span>Source</span><select class="select" name="source">
      <option value="all">Both sources</option>
      <option value="bank-105" ${app.explanationFilters.source === "bank-105" ? "selected" : ""}>105 Question Bank</option>
      <option value="pretest-70" ${app.explanationFilters.source === "pretest-70" ? "selected" : ""}>70 Question Pre-Test</option>
    </select></label>
    <label class="field"><span>Topic</span><select class="select" name="topic"><option value="all">All topics</option>${topics.map((topic) => `<option value="${escapeHtml(topic)}" ${app.explanationFilters.topic === topic ? "selected" : ""}>${escapeHtml(topic)}</option>`).join("")}</select></label>
    <label class="field"><span>Question type</span><select class="select" name="type"><option value="all">All types</option>${types.map((type) => `<option value="${escapeHtml(type)}" ${app.explanationFilters.type === type ? "selected" : ""}>${escapeHtml(type.replaceAll("-", " "))}</option>`).join("")}</select></label>
  </form>`;
}

function explanationCardMarkup({ question, explanation }) {
  const bookmarked = app.state.bookmarks.includes(question.id);
  const sourceRefs = (question.sources || [])
    .map((source) => `${sourceLabel(source)}, page ${source.page}`)
    .join(" · ");
  return `<article class="explanation-card" data-question-id="${escapeHtml(question.id)}">
    <header class="explanation-card__header">
      <span class="explanation-card__number" aria-label="Question ${escapeHtml(question.id.replace("q-", ""))}">${escapeHtml(question.id.replace("q-", ""))}</span>
      <div class="explanation-card__identity">
        <div class="explanation-card__metadata">
          <span>${escapeHtml(question.type.replaceAll("-", " "))}</span>
          <span>${escapeHtml(question.topic || "General")}</span>
        </div>
        <p class="explanation-card__sources">${escapeHtml(sourceRefs)}</p>
      </div>
      <button class="btn btn--quiet explanation-bookmark" type="button" data-action="bookmark" data-id="${escapeHtml(question.id)}" aria-pressed="${bookmarked}">${bookmarked ? "★ Bookmarked" : "☆ Bookmark"}</button>
    </header>
    <section class="explanation-card__source" lang="en" dir="ltr">
      <p class="explanation-card__eyebrow">Original English question</p>
      <h2>${escapeHtml(question.prompt)}</h2>
    </section>
    ${renderArabicExplanation(question, explanation, { generatedStudyGuidance: false })}
  </article>`;
}

function explanationsMarkup() {
  const intro = heading(
    "Question Explanations",
    "Read each original question with a clear Arabic translation, answer reasoning, and revision note."
  );
  const notice = `<aside class="guidance-notice" role="note">
    <span class="guidance-notice__mark" aria-hidden="true">i</span>
    <div><strong>Generated study guidance</strong><p>Arabic translations and explanations were added for learning support. They are not official PDF explanations, and source answers remain unchanged.</p></div>
  </aside>`;

  if (app.explanationsError || !app.explanationPayload) {
    return `${intro}${notice}<div class="empty-state explanation-error" role="status"><strong>Question explanations are currently unavailable.</strong><p>${escapeHtml(app.explanationsError?.message || "The explanation data did not load.")} Practice, Mock Exam, and the Question Bank are still available.</p></div>`;
  }

  const filtered = searchExplanationEntries(
    app.questions,
    app.explanations,
    app.explanationFilters
  );
  const visible = limitExplanationEntries(filtered, app.visibleExplanationCount);
  const remaining = Math.max(0, filtered.length - visible.length);
  return `${intro}${notice}${explanationFiltersMarkup()}
    <section class="explanations-results" aria-labelledby="explanations-count">
      <div class="explanations-results__header">
        <h2 id="explanations-count" tabindex="-1">${filtered.length} ${filtered.length === 1 ? "explanation" : "explanations"}</h2>
        <span aria-live="polite">Showing ${visible.length} of ${filtered.length}</span>
      </div>
      ${
        visible.length
          ? `<div class="explanations-list">${visible.map(explanationCardMarkup).join("")}</div>`
          : `<div class="empty-state"><strong>No explanations match these filters.</strong><p>Try a different English or Arabic search term, source, topic, or type.</p></div>`
      }
      ${
        remaining
          ? `<div class="explanations-more"><button class="btn btn--secondary" type="button" data-action="show-more">Show more</button><span>${remaining} remaining</span></div>`
          : ""
      }
    </section>`;
}

function revisionMarkup() {
  const topics = [...new Set(app.questions.map((question) => question.topic))].sort();
  const revisionQuestions = filterQuestions(app.questions, app.revisionFilters);
  const summary = buildRevisionSummary(revisionQuestions, app.state);
  const weakRows = summary.weakTopics.length
    ? summary.weakTopics.map((topic) => `<div class="breakdown-row"><span><strong>${escapeHtml(topic.topic)}</strong><small>${topic.answered} answered • ${topic.wrong} currently wrong</small></span><strong>${topic.accuracy}%</strong></div>`).join("")
    : `<div class="empty-state"><strong>Complete some questions to identify weak topics.</strong></div>`;
  return `${heading("Revision Summary", "A focused summary built from your answers, mistakes, and saved questions.")}
    <form class="filter-bar" data-revision-filter-form>
      <label class="field"><span>Source</span><select class="select" name="source">
        <option value="all">Both sources</option>
        <option value="bank-105" ${app.revisionFilters.source === "bank-105" ? "selected" : ""}>105 Question Bank</option>
        <option value="pretest-70" ${app.revisionFilters.source === "pretest-70" ? "selected" : ""}>70 Question Pre-Test</option>
      </select></label>
      <label class="field"><span>Topic</span><select class="select" name="topic"><option value="all">All topics</option>${topics.map((topic) => `<option value="${escapeHtml(topic)}" ${app.revisionFilters.topic === topic ? "selected" : ""}>${escapeHtml(topic)}</option>`).join("")}</select></label>
    </form>
    <div class="revision-cards">
      <a class="mini-card" href="#/mistakes"><span>Mistakes to review</span><strong>${summary.mistakes.length}</strong></a>
      <a class="mini-card" href="#/bookmarks"><span>Bookmarked questions</span><strong>${summary.bookmarks.length}</strong></a>
      <div class="mini-card"><span>Topics attempted</span><strong>${summary.weakTopics.length}</strong></div>
    </div>
    <section class="section-block"><div class="section-header"><h2>Weak Topics</h2></div><div class="breakdown-list">${weakRows}</div></section>
    <section class="section-block"><div class="section-header"><h2>Quick Revision: Official Answers</h2></div>
      ${questionListMarkup([...summary.mistakes, ...summary.bookmarks.filter((question) => !summary.mistakes.includes(question))].slice(0, 20), "Mistakes and bookmarks will appear here for quick revision.", { showProgress: true })}
    </section>`;
}

function collectionMarkup(route) {
  const isMistakes = route === "mistakes";
  const selected = isMistakes
    ? app.questions.filter((question) => app.state.progress[question.id]?.status === "wrong")
    : app.questions.filter((question) => app.state.bookmarks.includes(question.id));
  const actions = selected.length
    ? `<button class="btn btn--primary" data-action="start-focused" data-ids="${selected.map((question) => question.id).join(",")}">Practice this collection</button>`
    : "";
  return `${heading(isMistakes ? "Mistakes" : "Bookmarks", isMistakes ? "Review your selected answer, the official answer, and attempt history." : "Your saved official questions and answers.", actions)}
    <section class="section-block section-block--flat">${questionListMarkup(selected, isMistakes ? "No current mistakes. Keep practicing." : "No bookmarks yet.", { showProgress: true })}</section>`;
}

function render() {
  clearInterval(app.timer);
  const route = currentRoute();
  document.querySelectorAll("[data-route]").forEach((item) => item.classList.toggle("is-active", item.dataset.route === route));

  if (route === "dashboard") main.innerHTML = dashboardMarkup();
  else if (route === "practice") {
    main.innerHTML = app.state.activePractice ? sessionMarkup(app.state.activePractice) : setupMarkup("practice");
  } else if (route === "exam") {
    main.innerHTML = app.state.activeExam ? sessionMarkup(app.state.activeExam) : setupMarkup("exam");
  } else if (route === "results" && app.finishedSession) main.innerHTML = resultsMarkup(app.finishedSession);
  else if (route === "bank") main.innerHTML = bankMarkup();
  else if (route === "explanations") main.innerHTML = explanationsMarkup();
  else if (route === "revision") main.innerHTML = revisionMarkup();
  else if (route === "mistakes" || route === "bookmarks") main.innerHTML = collectionMarkup(route);
  else main.innerHTML = dashboardMarkup();

  const session = route === "practice" ? app.state.activePractice : route === "exam" ? app.state.activeExam : null;
  if (session) {
    const question = questionForSession(session, session.questionIds[session.index]);
    applySavedResponse(question, session.answers[question.id]?.response);
    bindOrdering();
    if (session.mode === "exam" && session.durationMinutes) {
      app.timer = setInterval(() => {
        const remaining = getRemainingSeconds(session);
        const label = main.querySelector("[data-timer]");
        if (label) label.textContent = formatDuration(remaining);
        if (remaining === 0) completeActiveSession("exam", true);
      }, 1000);
    }
  }
  main.focus({ preventScroll: true });
  window.scrollTo({ top: 0, behavior: "instant" });
}

function bindOrdering() {
  main.querySelectorAll("[data-move]").forEach((button) => {
    button.addEventListener("click", () => {
      const row = button.closest("li");
      if (button.dataset.move === "up" && row.previousElementSibling) row.parentNode.insertBefore(row, row.previousElementSibling);
      if (button.dataset.move === "down" && row.nextElementSibling) row.parentNode.insertBefore(row.nextElementSibling, row);
    });
  });
}

function activeSession() {
  return currentRoute() === "exam" ? app.state.activeExam : app.state.activePractice;
}

function updateActiveSession(session) {
  persist({
    ...app.state,
    lastQuestionId: session.questionIds[session.index] || null,
    [session.mode === "exam" ? "activeExam" : "activePractice"]: session,
  });
}

function submitCurrentAnswer() {
  const session = activeSession();
  const question = questionForSession(session, session.questionIds[session.index]);
  const form = main.querySelector("[data-question-form]");
  const response = responseFromForm(question, form);
  const nextSession = answerSessionQuestion(session, question, response);
  updateActiveSession(nextSession);
  const result = nextSession.answers[question.id];
  if (session.mode !== "exam" && question.correctAnswer !== null && result.possible > 0) {
    persist(
      recordAttempt(app.state, {
        questionId: question.id,
        selectedAnswer: canonicalResponse(question, response),
        correct: result.correct,
        mode: session.mode,
      })
    );
  }
  if (session.mode === "practice") render();
  else {
    const next = moveSession(nextSession, 1);
    updateActiveSession(next);
    render();
  }
}

function completeActiveSession(mode, force = false) {
  const session = mode === "exam" ? app.state.activeExam : app.state.activePractice;
  if (!session) return;
  if (
    !force &&
    !confirm(
      `Finish this ${mode === "exam" ? "mock exam" : "practice session"} now? Unanswered questions will be counted as skipped.`
    )
  ) {
    return;
  }
  const finished = finishSession(session);
  let next = {
    ...app.state,
    [mode === "exam" ? "activeExam" : "activePractice"]: null,
    [mode === "exam" ? "exams" : "sessions"]: [
      ...app.state[mode === "exam" ? "exams" : "sessions"],
      finished,
    ],
  };
  if (mode === "exam") {
    for (const [questionId, answer] of Object.entries(finished.answers)) {
      const question = questionForSession(finished, questionId);
      if (question.correctAnswer !== null && answer.possible > 0) {
        next = recordAttempt(next, {
          questionId,
          selectedAnswer: canonicalResponse(question, answer.response),
          correct: answer.correct,
          mode: "exam",
        });
      }
    }
  }
  persist(next);
  app.finishedSession = finished;
  location.hash = "#/results";
  render();
}

function startSession(form) {
  const data = new FormData(form);
  const mode = form.dataset.mode;
  const status = data.get("status") || "all";
  const candidates = filterQuestions(app.questions, {
    source: data.get("source"),
    topic: data.get("topic"),
    type: data.get("type"),
    status: status === "bookmarked" ? "all" : status,
    bookmarked: status === "bookmarked",
    bookmarks: app.state.bookmarks,
    progress: app.state.progress,
  });
  let session = createSession(candidates, {
    mode,
    count: Number(data.get("count")),
    source: "all",
    topic: "all",
    durationMinutes: Number(data.get("durationMinutes") || 0),
    shuffle: data.get("shuffle") === "on",
    shuffleChoices: data.get("shuffleChoices") === "on",
    excludeReview: data.get("excludeReview") === "on",
  });
  if (session.config.shuffleChoices) {
    session = {
      ...session,
      questionOverrides: Object.fromEntries(
        session.questionIds.map((id) => [id, shuffleChoices(app.questionMap.get(id))])
      ),
    };
  }
  updateActiveSession(session);
  render();
}

function canonicalResponse(question, response) {
  if (!question.choiceOrder || response === null || response === undefined) return response;
  if (question.type === "mcq") return question.choiceOrder[response];
  if (question.type === "multi-select") {
    return response.map((index) => question.choiceOrder[index]).sort((a, b) => a - b);
  }
  return response;
}

function startFocusedPractice(ids) {
  const questions = ids.map((id) => app.questionMap.get(id)).filter(Boolean);
  const session = createSession(questions, {
    mode: "practice",
    count: questions.length,
    shuffle: false,
    excludeReview: false,
  });
  updateActiveSession(session);
  location.hash = "#/practice";
  render();
}

function downloadProgress() {
  const blob = new Blob([exportState(app.state)], { type: "application/json" });
  const url = URL.createObjectURL(blob);
  const link = document.createElement("a");
  link.href = url;
  link.download = `its-study-progress-${new Date().toISOString().slice(0, 10)}.json`;
  link.click();
  URL.revokeObjectURL(url);
}

main.addEventListener("submit", (event) => {
  if (event.target.matches("[data-setup-form]")) {
    event.preventDefault();
    startSession(event.target);
  }
  if (event.target.matches("[data-filter-form]")) event.preventDefault();
  if (event.target.matches("[data-explanation-filter-form]")) event.preventDefault();
});

main.addEventListener("input", (event) => {
  const explanationForm = event.target.closest("[data-explanation-filter-form]");
  if (explanationForm) {
    app.explanationFilters = Object.fromEntries(new FormData(explanationForm).entries());
    app.visibleExplanationCount = 15;
    main.innerHTML = explanationsMarkup();
    if (event.target.name === "search") {
      const search = main.querySelector('[data-explanation-filter-form] [name="search"]');
      search?.focus();
      search?.setSelectionRange(search.value.length, search.value.length);
    }
    return;
  }
  const form = event.target.closest("[data-filter-form]");
  if (!form) return;
  const data = new FormData(form);
  app.filters = Object.fromEntries(data.entries());
  main.innerHTML = bankMarkup();
  if (event.target.name === "search") {
    const search = main.querySelector('[name="search"]');
    search?.focus();
    search?.setSelectionRange(search.value.length, search.value.length);
  }
});

main.addEventListener("change", (event) => {
  const form = event.target.closest("[data-revision-filter-form]");
  if (!form) return;
  app.revisionFilters = Object.fromEntries(new FormData(form).entries());
  main.innerHTML = revisionMarkup();
});

main.addEventListener("click", (event) => {
  const button = event.target.closest("[data-action]");
  if (!button) return;
  const action = button.dataset.action;
  if (action === "continue-practice") {
    location.hash = "#/practice";
    return;
  }
  if (action === "continue-exam") {
    location.hash = "#/exam";
    return;
  }
  if (action === "start-focused" || action === "retry-wrong") {
    startFocusedPractice((button.dataset.ids || "").split(",").filter(Boolean));
    return;
  }
  if (action === "show-more") {
    const total = searchExplanationEntries(
      app.questions,
      app.explanations,
      app.explanationFilters
    ).length;
    app.visibleExplanationCount = increaseVisibleCount(
      app.visibleExplanationCount,
      total
    );
    main.innerHTML = explanationsMarkup();
    const nextShowMore = main.querySelector('[data-action="show-more"]');
    if (nextShowMore) nextShowMore.focus();
    else main.querySelector("#explanations-count")?.focus();
    return;
  }
  if (action === "export") downloadProgress();
  if (action === "import") fileInput.click();
  if (action === "reset") {
    if (confirm("Reset all saved answers, sessions, mistakes, and bookmarks?")) {
      app.state = resetState();
      toast("Progress reset.");
      render();
    }
  }
  if (action === "bookmark") {
    persist(toggleBookmark(app.state, button.dataset.id));
    toast(app.state.bookmarks.includes(button.dataset.id) ? "Question bookmarked." : "Bookmark removed.");
    if (currentRoute() === "explanations") main.innerHTML = explanationsMarkup();
    else render();
  }

  const session = activeSession();
  if (!session) return;
  if (action === "submit-answer") submitCurrentAnswer();
  if (action === "previous") {
    updateActiveSession(moveSession(session, -1));
    render();
  }
  if (action === "next") {
    if (session.index === session.questionIds.length - 1) completeActiveSession(session.mode);
    else {
      updateActiveSession(moveSession(session, 1));
      render();
    }
  }
  if (action === "goto") {
    updateActiveSession(goToSessionQuestion(session, button.dataset.index));
    render();
  }
  if (action === "flag") {
    const questionId = session.questionIds[session.index];
    updateActiveSession(toggleSessionFlag(session, questionId));
    render();
  }
  if (action === "finish-session") completeActiveSession(session.mode);
});

fileInput.addEventListener("change", async () => {
  const file = fileInput.files[0];
  if (!file) return;
  try {
    persist(importState(await file.text()));
    toast("Progress imported.");
    render();
  } catch (error) {
    toast(error.message, true);
  } finally {
    fileInput.value = "";
  }
});

function applyTheme(theme) {
  document.documentElement.dataset.theme = theme;
  const isDark = theme === "dark";
  themeLabel.textContent = isDark ? "Light" : "Dark";
  themeToggle.setAttribute("aria-label", isDark ? "Switch to light mode" : "Switch to dark mode");
}

themeToggle.addEventListener("click", () => {
  const next = document.documentElement.dataset.theme === "dark" ? "light" : "dark";
  localStorage.setItem("its-study-theme", next);
  persist({ ...app.state, theme: next });
  applyTheme(next);
});

sidebarCollapse.addEventListener("click", () => appShell.classList.toggle("is-collapsed"));
document.querySelector("#mobile-more").addEventListener("click", () => {
  location.hash = "#/revision";
});
window.addEventListener("hashchange", render);
window.addEventListener("keydown", (event) => {
  if (
    event.target.matches("input, select, textarea") ||
    event.target.isContentEditable
  ) {
    return;
  }
  const session = activeSession();
  if (!session) return;
  if (event.key === "ArrowLeft") main.querySelector('[data-action="previous"]')?.click();
  if (event.key === "ArrowRight") main.querySelector('[data-action="next"]')?.click();
  if (event.key === "Enter") main.querySelector('[data-action="submit-answer"]')?.click();
  if (/^[1-4]$/.test(event.key)) {
    const control = main.querySelector(
      `[data-question-form] [name="answer"][value="${Number(event.key) - 1}"]`
    );
    if (control) {
      if (control.type === "checkbox") control.checked = !control.checked;
      else control.checked = true;
    }
  }
  if (event.key.toLowerCase() === "t" || event.key.toLowerCase() === "f") {
    const value = event.key.toLowerCase() === "t" ? "true" : "false";
    const rows = [...main.querySelectorAll(".statement-row")];
    const row = rows.find((item) => !item.querySelector("input:checked")) || rows[0];
    const control = row?.querySelector(`input[value="${value}"]`);
    if (control) control.checked = true;
  }
  if (event.key.toLowerCase() === "b") {
    main.querySelector('[data-action="bookmark"]')?.click();
  }
});

async function start() {
  const savedTheme =
    localStorage.getItem("its-study-theme") ||
    app.state.theme ||
    (matchMedia("(prefers-color-scheme: dark)").matches ? "dark" : "light");
  applyTheme(savedTheme);
  try {
    const [bankResult, explanationsResult] = await Promise.allSettled([
      loadQuestionBank(),
      loadExplanations(),
    ]);
    if (bankResult.status === "rejected") throw bankResult.reason;
    app.bank = bankResult.value;
    app.questions = app.bank.questions;
    app.questionMap = new Map(app.questions.map((question) => [question.id, question]));
    if (explanationsResult.status === "fulfilled") {
      try {
        app.explanationPayload = validateExplanationPayload(
          explanationsResult.value,
          app.questions
        );
        app.explanations = app.explanationPayload.explanations;
      } catch (error) {
        app.explanationsError = error;
      }
    } else {
      app.explanationsError =
        explanationsResult.reason instanceof Error
          ? explanationsResult.reason
          : new Error("The explanation data could not be loaded.");
    }
    render();
  } catch (error) {
    main.innerHTML = `<div class="empty-state"><strong>The official question bank could not be loaded.</strong><p>${escapeHtml(error.message)} Run the website from a simple local server.</p></div>`;
  }
}

start();
