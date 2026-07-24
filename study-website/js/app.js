import { loadQuestionBank } from "./questions.js";

const main = document.querySelector("#main-content");
const appShell = document.querySelector("#app-shell");
const themeToggle = document.querySelector("#theme-toggle");
const themeLabel = document.querySelector("#theme-toggle-label");
const sidebarCollapse = document.querySelector("#sidebar-collapse");

const app = {
  bank: null,
  questions: [],
};

function icon(name) {
  const paths = {
    play: '<path d="m8 5 11 7-11 7Z"/>',
    exam: '<path d="M6 3h9l4 4v14H6Z"/><path d="M14 3v5h5M9 13h6M9 17h6"/>',
    arrow: '<path d="m9 18 6-6-6-6"/>',
    mistakes: '<circle cx="12" cy="12" r="9"/><path d="m9 9 6 6m0-6-6 6"/>',
    bookmark: '<path d="M6 3h12v18l-6-4-6 4Z"/>',
    inbox: '<path d="M4 5h16l2 10v4H2v-4Z"/><path d="M2 15h6l2 2h4l2-2h6"/>',
  };
  return `<svg aria-hidden="true" viewBox="0 0 24 24">${paths[name] || ""}</svg>`;
}

function dashboardMarkup() {
  const sourceEntries = app.bank.sourceEntryCount;
  const uniqueQuestions = app.questions.length;
  return `
    <header class="page-header">
      <div>
        <h1>Dashboard</h1>
      </div>
    </header>

    <section class="progress-panel" aria-label="Overall progress">
      <div class="progress-panel__main">
        <div class="progress-panel__section">
          <div class="metric-label">Completion</div>
          <div class="metric-value metric-value--primary">0%</div>
          <div class="progress-track" aria-label="0% complete">
            <div class="progress-track__fill" style="--progress: 0%"></div>
          </div>
          <p class="metric-help">Your progress will appear here.</p>
        </div>
        <div class="progress-panel__section">
          <div class="metric-label">Accuracy</div>
          <div class="metric-value">—</div>
          <p class="metric-help">Complete questions to see your accuracy.</p>
        </div>
      </div>
      <div class="metric-strip">
        <div class="metric-strip__item">
          <span class="metric-label">Unique questions</span>
          <strong class="metric-strip__value metric-value--primary">${uniqueQuestions}</strong>
        </div>
        <div class="metric-strip__item">
          <span class="metric-label">Source entries</span>
          <strong class="metric-strip__value">${sourceEntries}</strong>
        </div>
        <div class="metric-strip__item">
          <span class="metric-label">Answered</span>
          <strong class="metric-strip__value">0</strong>
        </div>
        <div class="metric-strip__item">
          <span class="metric-label">Correct</span>
          <strong class="metric-strip__value metric-value--success">0</strong>
        </div>
        <div class="metric-strip__item">
          <span class="metric-label">Wrong</span>
          <strong class="metric-strip__value metric-value--danger">0</strong>
        </div>
      </div>
    </section>

    <div class="dashboard-actions">
      <a class="btn btn--primary" href="#/practice">${icon("play")}Start Practice</a>
      <a class="btn btn--primary" href="#/exam">${icon("exam")}Start Mock Exam</a>
      <button class="btn btn--secondary" type="button" disabled>${icon("arrow")}Continue Practice</button>
      <a class="btn btn--secondary" href="#/mistakes">${icon("mistakes")}Review Mistakes</a>
      <a class="btn btn--secondary" href="#/bookmarks">${icon("bookmark")}Review Bookmarks</a>
    </div>

    <section class="section-block">
      <div class="section-header"><h2>Recent Activity</h2></div>
      <div class="empty-state">
        ${icon("inbox")}
        <strong>No recent activity yet.</strong>
        <p>Start practicing to see your sessions here.</p>
      </div>
    </section>

    <section class="section-block">
      <div class="section-header"><h2>Revision Summary (Preview)</h2></div>
      <div class="empty-state">
        <strong>Build your revision summary through practice.</strong>
        <p>Weak topics, mistakes, and bookmarked official answers will appear here.</p>
      </div>
    </section>
  `;
}

function placeholderMarkup(route) {
  const labels = {
    practice: ["Practice", "Choose a focused practice session."],
    exam: ["Mock Exam", "Create a timed or untimed mock exam."],
    bank: ["Question Bank", "Search all official source questions."],
    revision: ["Revision Summary", "Review official answers and your weak topics."],
    mistakes: ["Mistakes", "Questions answered incorrectly will appear here."],
    bookmarks: ["Bookmarks", "Saved questions will appear here."],
  };
  const [title, copy] = labels[route] || labels.bank;
  return `
    <header class="page-header">
      <div><h1>${title}</h1><p>${copy}</p></div>
    </header>
    <section class="section-block">
      <div class="empty-state">
        ${icon("inbox")}
        <strong>This study tool is loading its controls.</strong>
      </div>
    </section>
  `;
}

function currentRoute() {
  const value = location.hash.replace(/^#\//, "").split("/")[0];
  return value || "dashboard";
}

function render() {
  const route = currentRoute();
  document.querySelectorAll("[data-route]").forEach((item) => {
    item.classList.toggle("is-active", item.dataset.route === route);
  });
  main.innerHTML = route === "dashboard" ? dashboardMarkup() : placeholderMarkup(route);
  main.focus({ preventScroll: true });
  window.scrollTo({ top: 0, behavior: "instant" });
}

function applyTheme(theme) {
  document.documentElement.dataset.theme = theme;
  const isDark = theme === "dark";
  themeLabel.textContent = isDark ? "Light" : "Dark";
  themeToggle.setAttribute(
    "aria-label",
    isDark ? "Switch to light mode" : "Switch to dark mode"
  );
}

themeToggle.addEventListener("click", () => {
  const next = document.documentElement.dataset.theme === "dark" ? "light" : "dark";
  localStorage.setItem("its-study-theme", next);
  applyTheme(next);
});

sidebarCollapse.addEventListener("click", () => {
  appShell.classList.toggle("is-collapsed");
});

window.addEventListener("hashchange", render);

async function start() {
  const savedTheme =
    localStorage.getItem("its-study-theme") ||
    (matchMedia("(prefers-color-scheme: dark)").matches ? "dark" : "light");
  applyTheme(savedTheme);
  try {
    app.bank = await loadQuestionBank();
    app.questions = app.bank.questions;
    render();
  } catch (error) {
    main.innerHTML = `
      <div class="empty-state">
        <strong>The official question bank could not be loaded.</strong>
        <p>${error.message} Run the website from a simple local server.</p>
      </div>
    `;
  }
}

start();
