import { filterQuestions, loadQuestionBank } from "./questions.js";
import {
  escapeHtml,
  normalizeResponse,
  renderAnswerReview,
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
  state: loadState(),
  finishedSession: null,
  filters: { search: "", source: "all", type: "all", topic: "all", status: "all" },
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
          ${
            isExam
              ? `<label class="field"><span>Time limit</span><select class="select" name="durationMinutes">
                  <option value="0">Untimed</option><option value="20">20 minutes</option><option value="45">45 minutes</option><option value="60">60 minutes</option>
                </select></label>`
              : ""
          }
        </div>
        <label class="checkbox-row"><input type="checkbox" name="shuffle" checked> Shuffle question order</label>
        <label class="checkbox-row"><input type="checkbox" name="excludeReview"> Exclude the one unresolved source-conflict item</label>
        <button class="btn btn--primary" type="submit">${isExam ? "Start Mock Exam" : "Start Practice"}</button>
      </form>
    </section>`;
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
  const question = app.questionMap.get(session.questionIds[session.index]);
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
    <div class="page-actions"><a class="btn btn--primary" href="#/${session.mode}">Start another</a><a class="btn btn--secondary" href="#/mistakes">Review mistakes</a></div>
    <section class="section-block"><div class="section-header"><h2>Answer Review</h2></div>
      <div class="revision-list">${session.questionIds.map((id, index) => {
        const question = app.questionMap.get(id);
        const answer = session.answers[id];
        return `<details class="revision-item"><summary><span>${index + 1}. ${escapeHtml(question.prompt)}</span><span class="tag">${answer ? (answer.correct ? "Correct" : "Wrong") : "Skipped"}</span></summary>${renderAnswerReview(question, answer?.response ?? null)}</details>`;
      }).join("")}</div>
    </section>`;
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
  </form>`;
}

function questionListMarkup(questions, emptyCopy = "No questions match these filters.") {
  if (!questions.length) return `<div class="empty-state"><strong>${escapeHtml(emptyCopy)}</strong></div>`;
  return `<div class="bank-list">${questions.map((question) => {
    const status = app.state.progress[question.id]?.status || "unanswered";
    const sourceRefs = question.sources.map((source) => `${sourceLabel(source)} p.${source.page}`).join(" • ");
    return `<details class="bank-row">
      <summary>
        <span class="bank-row__number">${question.id.replace("q-", "")}</span>
        <span class="bank-row__prompt">${escapeHtml(question.prompt)}<small class="bank-row__meta">${escapeHtml(question.topic)} • ${escapeHtml(sourceRefs)}</small></span>
        <span class="tag tag--${status}">${status}</span>
      </summary>
      <div class="bank-row__details">
        ${renderQuestion(question)}
        ${renderAnswerReview(question, null)}
        <button class="btn btn--secondary" data-action="bookmark" data-id="${question.id}">${app.state.bookmarks.includes(question.id) ? "★ Remove bookmark" : "☆ Bookmark"}</button>
      </div>
    </details>`;
  }).join("")}</div>`;
}

function bankMarkup() {
  const filtered = filterQuestions(app.questions, { ...app.filters, progress: app.state.progress });
  return `${heading("Question Bank", `Browse ${app.questions.length} unique questions covering all ${app.bank.sourceEntryCount} source entries.`)}
    ${bankFiltersMarkup()}
    <section class="section-block section-block--flat"><div class="section-header"><h2>${filtered.length} questions</h2><span>Official PDF content only</span></div>${questionListMarkup(filtered)}</section>`;
}

function revisionMarkup() {
  const summary = buildRevisionSummary(app.questions, app.state);
  const weakRows = summary.weakTopics.length
    ? summary.weakTopics.map((topic) => `<div class="breakdown-row"><span><strong>${escapeHtml(topic.topic)}</strong><small>${topic.answered} answered • ${topic.wrong} currently wrong</small></span><strong>${topic.accuracy}%</strong></div>`).join("")
    : `<div class="empty-state"><strong>Complete some questions to identify weak topics.</strong></div>`;
  return `${heading("Revision Summary", "A focused summary built from your answers, mistakes, and saved questions.")}
    <div class="revision-cards">
      <a class="mini-card" href="#/mistakes"><span>Mistakes to review</span><strong>${summary.mistakes.length}</strong></a>
      <a class="mini-card" href="#/bookmarks"><span>Bookmarked questions</span><strong>${summary.bookmarks.length}</strong></a>
      <div class="mini-card"><span>Topics attempted</span><strong>${summary.weakTopics.length}</strong></div>
    </div>
    <section class="section-block"><div class="section-header"><h2>Weak Topics</h2></div><div class="breakdown-list">${weakRows}</div></section>
    <section class="section-block"><div class="section-header"><h2>Quick Revision: Official Answers</h2></div>
      ${questionListMarkup([...summary.mistakes, ...summary.bookmarks.filter((question) => !summary.mistakes.includes(question))].slice(0, 20), "Mistakes and bookmarks will appear here for quick revision.")}
    </section>`;
}

function collectionMarkup(route) {
  const isMistakes = route === "mistakes";
  const selected = isMistakes
    ? app.questions.filter((question) => app.state.progress[question.id]?.status === "wrong")
    : app.questions.filter((question) => app.state.bookmarks.includes(question.id));
  return `${heading(isMistakes ? "Mistakes" : "Bookmarks", isMistakes ? "Review questions whose latest answer was incorrect." : "Your saved official questions and answers.")}
    <section class="section-block section-block--flat">${questionListMarkup(selected, isMistakes ? "No current mistakes. Keep practicing." : "No bookmarks yet.")}</section>`;
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
  else if (route === "revision") main.innerHTML = revisionMarkup();
  else if (route === "mistakes" || route === "bookmarks") main.innerHTML = collectionMarkup(route);
  else main.innerHTML = dashboardMarkup();

  const session = route === "practice" ? app.state.activePractice : route === "exam" ? app.state.activeExam : null;
  if (session) {
    const question = app.questionMap.get(session.questionIds[session.index]);
    applySavedResponse(question, session.answers[question.id]?.response);
    bindOrdering();
    if (session.mode === "exam" && session.durationMinutes) {
      app.timer = setInterval(() => {
        const remaining = getRemainingSeconds(session);
        const label = main.querySelector("[data-timer]");
        if (label) label.textContent = formatDuration(remaining);
        if (remaining === 0) completeActiveSession("exam");
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
  persist({ ...app.state, [session.mode === "exam" ? "activeExam" : "activePractice"]: session });
}

function submitCurrentAnswer() {
  const session = activeSession();
  const question = app.questionMap.get(session.questionIds[session.index]);
  const form = main.querySelector("[data-question-form]");
  const response = responseFromForm(question, form);
  const nextSession = answerSessionQuestion(session, question, response);
  updateActiveSession(nextSession);
  const result = nextSession.answers[question.id];
  if (session.mode !== "exam" && question.correctAnswer !== null && result.possible > 0) {
    persist(
      recordAttempt(app.state, {
        questionId: question.id,
        selectedAnswer: response,
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

function completeActiveSession(mode) {
  const session = mode === "exam" ? app.state.activeExam : app.state.activePractice;
  if (!session) return;
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
      const question = app.questionMap.get(questionId);
      if (question.correctAnswer !== null && answer.possible > 0) {
        next = recordAttempt(next, {
          questionId,
          selectedAnswer: answer.response,
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
  const session = createSession(app.questions, {
    mode,
    count: Number(data.get("count")),
    source: data.get("source"),
    topic: data.get("topic"),
    durationMinutes: Number(data.get("durationMinutes") || 0),
    shuffle: data.get("shuffle") === "on",
    excludeReview: data.get("excludeReview") === "on",
  });
  updateActiveSession(session);
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
});

main.addEventListener("input", (event) => {
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

main.addEventListener("click", (event) => {
  const button = event.target.closest("[data-action]");
  if (!button) return;
  const action = button.dataset.action;
  if (action === "continue-practice") {
    location.hash = "#/practice";
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
    render();
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
  applyTheme(next);
});

sidebarCollapse.addEventListener("click", () => appShell.classList.toggle("is-collapsed"));
document.querySelector("#mobile-more").addEventListener("click", () => {
  location.hash = "#/revision";
});
window.addEventListener("hashchange", render);
window.addEventListener("keydown", (event) => {
  if (event.target.matches("input, select, textarea")) return;
  const session = activeSession();
  if (!session) return;
  if (event.key === "ArrowLeft") main.querySelector('[data-action="previous"]')?.click();
  if (event.key === "ArrowRight") main.querySelector('[data-action="next"]')?.click();
  if (event.key === "Enter") main.querySelector('[data-action="submit-answer"]')?.click();
});

async function start() {
  const savedTheme =
    localStorage.getItem("its-study-theme") ||
    (matchMedia("(prefers-color-scheme: dark)").matches ? "dark" : "light");
  applyTheme(savedTheme);
  try {
    app.bank = await loadQuestionBank();
    app.questions = app.bank.questions;
    app.questionMap = new Map(app.questions.map((question) => [question.id, question]));
    render();
  } catch (error) {
    main.innerHTML = `<div class="empty-state"><strong>The official question bank could not be loaded.</strong><p>${escapeHtml(error.message)} Run the website from a simple local server.</p></div>`;
  }
}

start();
