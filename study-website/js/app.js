import { filterLessons, loadCourseData } from "./data.js";
import { filterQuestions, isExamEligible, isScoreable } from "./questions.js";
import { answerPracticeQuestion, createPracticeSession, goToPracticeQuestion, movePracticeQuestion } from "./quiz.js";
import { answerExamQuestion, createExam, getExamRemainingSeconds, goToExamQuestion, hydrateExam, moveExamQuestion, submitExam, toggleExamBookmark, toggleExamFlag } from "./exam.js";
import { BACKUP_STORAGE_KEY, clearActiveExam, exportState, importState, loadState, markLessonComplete, recordAttempt, recordSessionSummary, resetState, saveState, setActiveExam, toggleBookmark } from "./storage.js";
import { getBookmarkedLessons, getBookmarkedQuestions, getMistakeQuestions, getRevisionSummary } from "./revision.js";

const THEME_KEY = "os-study-theme-v1";
const PAGE_SIZE = 10;
const ROUTE_TITLES = { dashboard: "Dashboard", material: "Material", questions: "Question Bank", explanations: "Question Explanations", practice: "Practice", exam: "Mock Exam", revision: "Revision", mistakes: "Mistakes", bookmarks: "Bookmarks", settings: "Settings" };
const ICONS = {
  home: '<path d="m3 10 9-7 9 7v10a1 1 0 0 1-1 1h-5v-7H9v7H4a1 1 0 0 1-1-1Z"/>',
  book: '<path d="M4 5.5A2.5 2.5 0 0 1 6.5 3H20v17H6.5A2.5 2.5 0 0 0 4 22.5Z"/><path d="M4 5.5v17M8 7h8"/>',
  pencil: '<path d="m4 20 4.2-1 11-11a2.4 2.4 0 0 0-3.4-3.4l-11 11Z"/><path d="m14.5 6 3.5 3.5"/>',
  file: '<path d="M6 3h9l4 4v14H6Z"/><path d="M14 3v5h5M9 13h6M9 17h6"/>',
  layers: '<path d="m4 7 8-4 8 4-8 4Z"/><path d="m4 12 8 4 8-4M4 17l8 4 8-4"/>',
  translation: '<path d="M4 5h11M9 3v2m-4 0c1 4 3 6 6 8m1-4 4 10m-3-3h6"/>',
  chart: '<path d="M4 20V10m6 10V4m6 16v-7m4 7H2"/>',
  "circle-x": '<circle cx="12" cy="12" r="9"/><path d="m9 9 6 6m0-6-6 6"/>',
  bookmark: '<path d="M6 3h12v18l-6-4-6 4Z"/>',
  settings: '<circle cx="12" cy="12" r="3"/><path d="M19 12a7 7 0 0 0-.2-1.7l2-1.5-2-3.4-2.4 1a7 7 0 0 0-2.8-1.6L13.3 2H9.4L9 4.8a7 7 0 0 0-2.8 1.6l-2.4-1-2 3.4 2 1.5A7 7 0 0 0 3.6 12c0 .6.1 1.2.2 1.7l-2 1.5 2 3.4 2.4-1A7 7 0 0 0 9 19.2l.4 2.8h3.9l.4-2.8a7 7 0 0 0 2.8-1.6l2.4 1 2-3.4-2-1.5c.1-.5.1-1.1.1-1.7Z"/>',
  play: '<path d="m8 5 11 7-11 7Z"/>',
  download: '<path d="M12 3v12m0 0 5-5m-5 5-5-5M4 20h16"/>',
  upload: '<path d="M12 17V5m0 0 5 5m-5-5-5 5M4 20h16"/>'
};

export function escapeHtml(value) {
  if (value === null || value === undefined) return "";
  return String(value).replace(/[&<>"']/g, function (character) {
    return { "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#39;" }[character];
  });
}

export function routeFromHash(hash) {
  const value = typeof hash === "string" ? hash : "";
  if (!value.startsWith("#/")) return { name: "not-found" };
  const raw = value.slice(2);
  if (!raw || raw.includes("?") || raw.includes("#") || raw.includes("//")) return { name: "not-found" };
  if (raw === "bank") return { name: "questions" };
  if (Object.hasOwn(ROUTE_TITLES, raw)) return { name: raw };
  const lesson = raw.match(/^lesson\/(lesson-)?(os-[a-z0-9-]+)$/);
  return lesson ? { name: "lesson", id: "lesson-" + lesson[2] } : { name: "not-found" };
}

export function shouldHandleShortcut(event) {
  if (!event || event.defaultPrevented || event.ctrlKey || event.metaKey || event.altKey) return false;
  const target = event.target;
  const tag = String(target && target.tagName || "").toUpperCase();
  if (["INPUT", "TEXTAREA", "SELECT", "BUTTON", "A"].includes(tag) || target && target.isContentEditable) return false;
  if (target && typeof target.closest === "function" && target.closest("[contenteditable='true']")) return false;
  return ["1", "2", "3", "4", "t", "T", "f", "F", "ArrowLeft", "ArrowRight", "b", "B", "s", "S"].includes(event.key);
}

export function navigationRenderDecision(currentHash, targetHash) {
  const current = typeof currentHash === "string" ? currentHash : "";
  const target = typeof targetHash === "string" ? targetHash : "";
  return { setHash: current !== target, renderNow: current === target };
}

export function getDashboardCoverage(data) {
  return { modules: Array.isArray(data?.modules) ? data.modules.length : 0, lessons: Array.isArray(data?.lessons) ? data.lessons.length : 0 };
}

export function lessonSectionLanguage(section) {
  return section?.origin === "generated" && section?.generatedStudyGuidance === true
    ? { lang: "ar", dir: "rtl", className: "material-section arabic" }
    : { lang: "en", dir: "ltr", className: "material-section" };
}

export function renderLessonGroup(title, entries, renderCitation) {
  if (!Array.isArray(entries) || !entries.length) return "";
  const cite = typeof renderCitation === "function" ? renderCitation : function () { return ""; };
  const items = entries.map(function (entry) {
    if (!entry || typeof entry !== "object") return "";
    if (Object.hasOwn(entry, "misconception") || Object.hasOwn(entry, "correction")) {
      if (!entry.misconception || !entry.correction) return "";
      return "<li><strong>Misconception:</strong> " + escapeHtml(entry.misconception) + "<br><strong>Correction:</strong> " + escapeHtml(entry.correction) + " " + cite(entry.sourceRefs) + "</li>";
    }
    if (!entry.body) return "";
    return "<li>" + escapeHtml(entry.body) + " " + cite(entry.sourceRefs) + "</li>";
  }).filter(Boolean).join("");
  return items ? "<section><h3>" + escapeHtml(title) + '</h3><ul class="content-list">' + items + "</ul></section>" : "";
}

export function getPracticeQuestionView(session, question, explanation) {
  const answer = session?.answers?.[question?.id];
  if (!answer) return { locked: false, response: undefined, feedback: null };
  return {
    locked: true,
    response: answer.response,
    feedback: {
      questionId: question.id,
      ...answer,
      rationale: question.rationale ?? null,
      sourceRefs: question.sourceRefs ?? [],
      explanation: explanation ?? null,
    },
  };
}

export function getSetupSummary(mode, questions, setup = {}, course = {}, indexes = {}) {
  const scoped = filterQuestions(questions, setup, indexes);
  const eligible = scoped.filter(function (question) { return mode === "exam" ? isExamEligible(question, course) : isScoreable(question); });
  const fallbackCount = mode === "exam" ? Number(course?.exam?.defaultCount) || 25 : 10;
  const count = Number(setup.count);
  const validCount = Number.isInteger(count) && count > 0;
  const requestedCount = validCount ? count : fallbackCount;
  const fallbackMinutes = Number(course?.exam?.defaultMinutes) || 30;
  const rawMinutes = Number(setup.minutes);
  const validMinutes = Number.isInteger(rawMinutes) && rawMinutes > 0;
  const minutes = mode === "exam" ? (validMinutes ? rawMinutes : fallbackMinutes) : null;
  let message = "Ready to start.";
  if (!validCount) message = "Enter a positive question count.";
  else if (mode === "exam" && !validMinutes) message = "Enter a positive number of minutes for the Mock Exam.";
  else if (!eligible.length) message = "No eligible questions match the selected scope.";
  else if (requestedCount > eligible.length) message = "Only " + eligible.length + " eligible questions match this scope.";
  return { scopeCount: scoped.length, eligibleCount: eligible.length, requestedCount: requestedCount, minutes: minutes, canStart: validCount && eligible.length > 0 && requestedCount <= eligible.length && (mode !== "exam" || validMinutes), message: message };
}

export function trapDialogFocus(event, controls) {
  if (!event || event.key !== "Tab" || !Array.isArray(controls) || !controls.length) return false;
  const index = controls.indexOf(event.target);
  const target = event.shiftKey ? (index <= 0 ? controls[controls.length - 1] : null) : (index === controls.length - 1 || index < 0 ? controls[0] : null);
  if (!target) return false;
  event.preventDefault();
  target.focus();
  return true;
}

function html() { return Array.from(arguments).join(""); }
function icon(name) { return '<svg aria-hidden="true" viewBox="0 0 24 24">' + (ICONS[name] || "") + "</svg>"; }
function emptyFilters() { return { search: "", moduleId: "all", sourceId: "all", completion: "all", lessonId: "all", topic: "all", type: "all", difficulty: "all", bloomLevel: "all", status: "all" }; }
const app = { data: null, state: null, practice: null, exam: null, practiceResult: null, examResult: null, timer: null, revealed: new Set(), pages: { questions: 1, explanations: 1 }, filters: { material: emptyFilters(), questions: emptyFilters(), explanations: emptyFilters() }, setups: {}, focusReturn: null };

function canonical() { return app.data ? { lessons: app.data.lessons, questions: app.data.questions } : undefined; }
function moduleFor(id) { return app.data.moduleById[id]; }
function sourceFor(id) { return app.data.course.sources.find(function (source) { return source.id === id; }); }
function citation(refs) {
  if (!refs || !refs.length) return "";
  return '<span class="citation" lang="en" dir="ltr">' + refs.map(function (ref) { return escapeHtml((sourceFor(ref.sourceId) || {}).label || ref.sourceId) + ", p. " + escapeHtml(ref.location); }).join(" · ") + "</span>";
}
function heading(title, copy, actions) {
  return '<header class="page-header"><div><h1 tabindex="-1">' + escapeHtml(title) + "</h1>" + (copy ? "<p>" + escapeHtml(copy) + "</p>" : "") + "</div>" + (actions ? '<div class="page-actions">' + actions + "</div>" : "") + "</header>";
}
function tag(text, css) { return '<span class="tag ' + (css || "") + '">' + escapeHtml(text) + "</span>"; }
function status(value) {
  if (value === "completed") return '<span class="status success">Completed</span>';
  if (value === "in-progress") return '<span class="status warning">In progress</span>';
  return '<span class="status">Not started</span>';
}
function save(next) { app.state = saveState(next, undefined, canonical()); return app.state; }
function notify(message, error) {
  const region = document.querySelector("#toast-region");
  if (!region) return;
  const item = document.createElement("div");
  item.className = "toast" + (error ? " error" : "");
  item.textContent = message;
  region.append(item);
  setTimeout(function () { item.remove(); }, 3600);
}
function select(records, chosen, label) {
  return '<option value="all">All ' + escapeHtml(label) + "</option>" + records.map(function (record) {
    const value = record.id || record;
    const title = record.title || record.label || record;
    return '<option value="' + escapeHtml(value) + '"' + (value === chosen ? " selected" : "") + ">" + escapeHtml(title) + "</option>";
  }).join("");
}
function routeFilters(kind, filters, advanced) {
  const topics = Array.from(new Set(app.data.questions.map(function (question) { return question.topic; }))).sort();
  return '<form class="filters" data-filter-form="' + kind + '">' +
    '<label class="field"><span>Search</span><input name="search" value="' + escapeHtml(filters.search) + '" placeholder="Search study content" /></label>' +
    '<label class="field"><span>Module</span><select name="moduleId">' + select(app.data.modules, filters.moduleId, "modules") + "</select></label>" +
    (kind === "material" ? '<label class="field"><span>Source</span><select name="sourceId">' + select(app.data.course.sources, filters.sourceId, "sources") + '</select></label><label class="field"><span>Completion</span><select name="completion"><option value="all">All progress</option><option value="completed"' + (filters.completion === "completed" ? " selected" : "") + '>Completed</option><option value="in-progress"' + (filters.completion === "in-progress" ? " selected" : "") + '>In progress</option><option value="unstarted"' + (filters.completion === "unstarted" ? " selected" : "") + ">Not started</option></select></label>" : "") +
    (advanced ? '<label class="field"><span>Lesson</span><select name="lessonId">' + select(app.data.lessons, filters.lessonId, "lessons") + '</select></label><label class="field"><span>Topic</span><select name="topic"><option value="all">All topics</option>' + topics.map(function (topic) { return '<option value="' + escapeHtml(topic) + '"' + (topic === filters.topic ? " selected" : "") + ">" + escapeHtml(topic) + "</option>"; }).join("") + '</select></label><label class="field"><span>Type</span><select name="type"><option value="all">All types</option><option value="mcq"' + (filters.type === "mcq" ? " selected" : "") + '>Multiple choice</option><option value="true-false"' + (filters.type === "true-false" ? " selected" : "") + '>True / False</option></select></label><label class="field"><span>Difficulty</span><select name="difficulty"><option value="all">All difficulty</option>' + ["easy", "medium", "hard"].map(function (value) { return '<option value="' + value + '"' + (value === filters.difficulty ? " selected" : "") + ">" + value + "</option>"; }).join("") + '</select></label><label class="field"><span>Bloom</span><select name="bloomLevel"><option value="all">All levels</option>' + ["remember", "apply", "analyze"].map(function (value) { return '<option value="' + value + '"' + (value === filters.bloomLevel ? " selected" : "") + ">" + value + "</option>"; }).join("") + '</select></label><label class="field"><span>Status</span><select name="status"><option value="all">All status</option><option value="bookmarked"' + (filters.status === "bookmarked" ? " selected" : "") + '>Bookmarked</option><option value="mistakes"' + (filters.status === "mistakes" ? " selected" : "") + '>Mistakes</option></select></label>' : "") +
    '<button class="btn btn--quiet" type="button" data-action="reset-filters" data-kind="' + kind + '">Reset filters</button></form>';
}
function filteredQuestions(filters) {
  return filterQuestions(app.data.questions, Object.assign({}, filters, {
    bookmarkedIds: filters.status === "bookmarked" ? app.state.bookmarks.questionIds : undefined,
    mistakeIds: filters.status === "mistakes" ? Object.keys(app.state.mistakes) : undefined
  }), app.data);
}
function contentGroup(title, entries) { return renderLessonGroup(title, entries, citation); }
function questionMeta(question) {
  return '<div class="question-meta">' + tag(question.type === "mcq" ? "Multiple choice" : "True / False") + tag(question.topic) + tag(question.difficulty) + tag(question.bloomLevel) + tag("Generated practice question", "generated") + citation(question.sourceRefs) + "</div>";
}
function navPages(kind, page, pages) {
  if (pages <= 1) return "";
  return '<nav class="pagination" aria-label="' + escapeHtml(kind) + ' pages"><button class="btn" data-action="page" data-kind="' + kind + '" data-page="' + (page - 1) + '"' + (page === 1 ? " disabled" : "") + ">Previous page</button><span>Page " + page + " of " + pages + '</span><button class="btn" data-action="page" data-kind="' + kind + '" data-page="' + (page + 1) + '"' + (page === pages ? " disabled" : "") + ">Next page</button></nav>";
}
function formatSeconds(seconds) {
  const safe = Math.max(0, Number(seconds) || 0);
  return Math.floor(safe / 60) + ":" + String(safe % 60).padStart(2, "0");
}

export function renderDashboard() {
  const summary = getRevisionSummary(app.data, app.state);
  const coverage = getDashboardCoverage(app.data);
  const completion = summary.lessons.total ? Math.round(summary.lessons.completed * 100 / summary.lessons.total) : 0;
  const recents = summary.recentSessions.length ? '<div class="recent-list">' + summary.recentSessions.map(function (item) {
    return '<div class="recent-row"><span><strong>' + escapeHtml(item.mode === "exam" ? "Mock Exam" : "Practice") + "</strong><small>" + escapeHtml(new Date(item.finishedAt).toLocaleString()) + "</small></span><strong>" + escapeHtml(item.scoreable ? item.percentage + "%" : "Unscored") + "</strong></div>";
  }).join("") + "</div>" : '<div class="empty-state"><strong>No recent activity yet.</strong><p>Start Practice or Mock Exam to see finalized sessions here.</p></div>';
  const weak = summary.weakModules.concat(summary.weakTopics);
  return heading("Dashboard", "Your source-backed Operating Systems study workspace.") +
    '<section class="panel metric-panel"><div class="metric-primary"><div class="metric-block"><span class="metric-label">Lesson completion</span><strong class="metric-number primary">' + completion + '%</strong><div class="progress-track"><span style="--value:' + completion + '%"></span></div><p class="metric-help">' + summary.lessons.completed + " of " + summary.lessons.total + ' lessons completed.</p></div><div class="metric-block"><span class="metric-label">Scoreable accuracy</span><strong class="metric-number">' + (summary.attempts.answered ? summary.attempts.accuracy + "%" : "—") + "</strong><p class=\"metric-help\">" + (summary.attempts.answered ? "Based on scoreable submitted responses." : "Answer a practice question to build an accuracy score.") + '</p></div></div><div class="metric-strip"><div><span class="metric-label">Modules</span><strong>' + coverage.modules + '</strong></div><div><span class="metric-label">Lessons</span><strong>' + coverage.lessons + '</strong></div><div><span class="metric-label">Sources</span><strong>' + app.data.course.sources.length + '</strong></div><div><span class="metric-label">Teaching pages</span><strong>' + escapeHtml(app.data.course.coverage.teachingPages) + '</strong></div><div><span class="metric-label">Questions</span><strong>' + app.data.questions.length + '</strong></div><div><span class="metric-label">Correct</span><strong class="success">' + summary.attempts.correct + '</strong></div><div><span class="metric-label">Wrong</span><strong class="error">' + summary.attempts.incorrect + "</strong></div></div></section>" +
    '<div class="action-row"><a class="btn btn--primary" href="#/practice">' + icon("play") + 'Start Practice</a><a class="btn btn--primary" href="#/exam">' + icon("file") + 'Start Mock Exam</a><a class="btn" href="#/material">Browse Material</a><a class="btn" href="#/mistakes">Review Mistakes</a><a class="btn" href="#/bookmarks">Review Bookmarks</a>' + (app.practice || app.state.activeExam ? '<a class="btn" href="#/' + (app.practice ? "practice" : "exam") + '">Resume active session</a>' : "") + "</div>" +
    '<section class="panel"><div class="section-title"><h2>Recent finalized sessions</h2></div>' + recents + '</section><section class="panel"><div class="section-title"><h2>Revision priorities</h2><a class="btn btn--quiet" href="#/revision">Open revision</a></div>' + (weak.length ? '<div class="revision-grid">' + weak.slice(0, 6).map(function (item) { return '<div><span class="metric-label">Needs review</span><strong>' + escapeHtml(item.title) + '</strong><span class="muted">' + escapeHtml(item.accuracy) + "% accuracy</span></div>"; }).join("") + "</div>" : '<div class="empty-state"><strong>No weak areas yet.</strong><p>Scoreable attempts will identify modules and topics that need another pass.</p></div>') + "</section>";
}

export function renderMaterial() {
  const filters = app.filters.material;
  const lessons = filterLessons(app.data.lessons, Object.assign({}, filters, { lessonProgress: app.state.lessonProgress }));
  return heading("Material", "Search the source-backed lessons, then read or practice linked content.") + routeFilters("material", filters, false) + '<p class="filter-result">' + lessons.length + " of " + app.data.lessons.length + " lessons shown.</p>" +
    (lessons.length ? lessons.map(function (lesson) {
      const progress = app.state.lessonProgress[lesson.id] && app.state.lessonProgress[lesson.id].status || "unstarted";
      const sources = Array.from(new Set(lesson.materialSections.flatMap(function (section) { return section.sourceRefs.map(function (ref) { return ref.sourceId; }); })));
      return '<article class="lesson-card"><div class="lesson-card__header"><div>' + tag((moduleFor(lesson.moduleId) || {}).title || lesson.moduleId) + " " + status(progress) + '</div><div class="page-actions"><a class="btn" href="#/lesson/' + escapeHtml(lesson.id) + '">Open lesson</a><button class="btn btn--quiet" data-action="practice-lesson" data-lesson="' + escapeHtml(lesson.id) + '">Practice</button></div></div><h2>' + escapeHtml(lesson.title) + "</h2><p>" + lesson.learningObjectives.length + " objectives · " + lesson.materialSections.length + " sections · " + sources.map(function (id) { return escapeHtml((sourceFor(id) || {}).label || id); }).join(", ") + "</p></article>";
    }).join("") : '<div class="empty-state"><strong>No lessons match these filters.</strong><p>Keep filters to refine your search, or reset them to see all material.</p><button class="btn" data-action="reset-filters" data-kind="material">Reset filters</button></div>');
}

export function renderLesson(route) {
  const lesson = app.data.lessonById[route.id];
  if (!lesson) return renderNotFound("That lesson is not available in this course.");
  const progress = app.state.lessonProgress[lesson.id] && app.state.lessonProgress[lesson.id].status || "unstarted";
  const bookmarked = app.state.bookmarks.lessonIds.includes(lesson.id);
  const actions = '<button class="btn" data-action="toggle-complete" data-lesson="' + escapeHtml(lesson.id) + '">' + (progress === "completed" ? "Mark in progress" : "Mark completed") + '</button><button class="btn" data-action="bookmark-lesson" data-lesson="' + escapeHtml(lesson.id) + '">' + (bookmarked ? "Remove bookmark" : "Bookmark lesson") + '</button><button class="btn btn--primary" data-action="practice-lesson" data-lesson="' + escapeHtml(lesson.id) + '">Start lesson Practice</button>';
  const sections = lesson.materialSections.map(function (section) {
    const language = lessonSectionLanguage(section);
    const terms = section.terms && section.terms.length ? '<dl class="term-list">' + section.terms.map(function (term) { return "<div><dt>" + escapeHtml(term.term) + "</dt><dd>" + escapeHtml(term.definition) + " " + citation(term.sourceRefs) + "</dd></div>"; }).join("") + "</dl>" : "";
    const links = section.linkedQuestionIds && section.linkedQuestionIds.length ? '<p><a href="#/questions">Open ' + section.linkedQuestionIds.length + ' linked Question Bank record' + (section.linkedQuestionIds.length === 1 ? "" : "s") + '</a> · <a href="#/explanations">Read bilingual explanations</a></p>' : "";
    return '<article class="' + language.className + '" lang="' + language.lang + '" dir="' + language.dir + '"><span class="origin-label" lang="en" dir="ltr">' + escapeHtml(section.label || (section.generatedStudyGuidance ? "Generated study guidance" : "Source material")) + "</span><h2>" + escapeHtml(section.title) + "</h2>" + section.summaries.map(function (entry) { return "<p>" + escapeHtml(entry.body) + " " + citation(entry.sourceRefs) + "</p>"; }).join("") + terms + contentGroup("Worked examples", section.examples) + contentGroup("Common mistakes", section.mistakes) + contentGroup("Exam tips", section.examTips) + contentGroup("Recap", section.recaps) + links + "</article>";
  }).join("");
  return heading(lesson.title, (moduleFor(lesson.moduleId) || {}).title || lesson.moduleId, actions) + '<section class="panel lesson-intro"><div>' + status(progress) + "</div><h2>Learning objectives</h2><ol class=\"objective-list\">" + lesson.learningObjectives.map(function (objective) { return "<li>" + escapeHtml(objective.text) + " " + citation(objective.sourceRefs) + "</li>"; }).join("") + '</ol></section><section class="panel">' + sections + "</section>";
}

function previewQuestion(question) {
  const shown = app.revealed.has(question.id);
  const answer = question.type === "mcq" ? question.options[question.correctAnswer] : question.correctAnswer ? "True" : "False";
  const mark = app.state.bookmarks.questionIds.includes(question.id) ? "Remove bookmark" : "Bookmark";
  return '<article class="question-card">' + questionMeta(question) + '<h2 lang="en" dir="ltr">' + escapeHtml(question.prompt) + '</h2><div class="question-card__footer"><div><button class="btn btn--quiet" data-action="reveal-answer" data-question="' + escapeHtml(question.id) + '">' + (shown ? "Hide answer" : "Show answer") + "</button>" + (shown ? "<p><strong>Answer:</strong> " + escapeHtml(answer) + "</p><p>" + escapeHtml(question.rationale) + '</p><a href="#/explanations">Read Arabic guidance</a>' : "") + '</div><button class="btn btn--quiet" data-action="bookmark-question" data-question="' + escapeHtml(question.id) + '">' + mark + "</button></div></article>";
}
export function renderQuestions() {
  const rows = filteredQuestions(app.filters.questions);
  const pages = Math.max(1, Math.ceil(rows.length / PAGE_SIZE));
  app.pages.questions = Math.min(app.pages.questions, pages);
  const page = app.pages.questions;
  return heading("Question Bank", "Find source-grounded questions and explicitly reveal answers when you are ready to study.") + routeFilters("questions", app.filters.questions, true) + '<p class="filter-result">' + rows.length + " result" + (rows.length === 1 ? "" : "s") + " · page " + page + " of " + pages + "</p>" + (rows.length ? rows.slice((page - 1) * PAGE_SIZE, page * PAGE_SIZE).map(previewQuestion).join("") : '<div class="empty-state"><strong>No questions match these filters.</strong><p>Your filters are still active. Reset them to return to all questions.</p><button class="btn" data-action="reset-filters" data-kind="questions">Reset filters</button></div>') + navPages("questions", page, pages);
}

export function renderExplanations() {
  const rows = filteredQuestions(app.filters.explanations);
  const pages = Math.max(1, Math.ceil(rows.length / PAGE_SIZE));
  app.pages.explanations = Math.min(app.pages.explanations, pages);
  const page = app.pages.explanations;
  const visible = rows.slice((page - 1) * PAGE_SIZE, page * PAGE_SIZE);
  const records = visible.map(function (question) {
    const arabic = app.data.explanationByQuestionId[question.id];
    return '<article class="explanation-card">' + questionMeta(question) + '<h2 lang="en" dir="ltr">' + escapeHtml(question.prompt) + '</h2>' + (arabic ? '<div class="arabic" lang="ar" dir="rtl"><h3>الترجمة والشرح</h3><p>' + escapeHtml(arabic.translation) + "</p>" + arabic.explanation.map(function (paragraph) { return "<p>" + escapeHtml(paragraph) + "</p>"; }).join("") + "<p><strong>ملاحظة مراجعة:</strong> " + escapeHtml(arabic.note) + "</p></div>" + citation(arabic.sourceRefs) : '<p class="muted">Arabic study guidance is unavailable for this record.</p>') + "</article>";
  }).join("");
  return heading("Question Explanations", "Read the original English prompt alongside the complete Arabic study guidance.") + routeFilters("explanations", app.filters.explanations, true) + '<p class="filter-result">' + rows.length + " bilingual explanation record" + (rows.length === 1 ? "" : "s") + '.</p><section class="panel">' + (records || '<div class="empty-state"><strong>No explanations match these filters.</strong><p>Reset filters to return to the complete bilingual guidance set.</p></div>') + "</section>" + navPages("explanations", page, pages);
}

function setupDefaults(mode) {
  return { moduleId: "all", lessonId: "all", topic: "all", type: "all", difficulty: "all", bloomLevel: "all", order: "original", count: String(mode === "exam" ? app.data.course.exam.defaultCount : 10), minutes: String(app.data.course.exam.defaultMinutes) };
}
function setupValues(mode) {
  if (!app.setups[mode]) app.setups[mode] = setupDefaults(mode);
  return app.setups[mode];
}
function setupScope(mode) {
  const topics = Array.from(new Set(app.data.questions.map(function (question) { return question.topic; }))).sort();
  const exam = mode === "exam";
  const values = setupValues(mode);
  const summary = getSetupSummary(mode, app.data.questions, values, app.data.course, app.data);
  const selected = function (value, expected) { return value === expected ? " selected" : ""; };
  const summaryText = '<p class="setup-summary" role="status"><strong>Selected scope:</strong> ' + summary.scopeCount + ' questions · <strong>Eligible:</strong> ' + summary.eligibleCount + ' · <strong>Requested:</strong> ' + summary.requestedCount + ' · <strong>Minutes:</strong> ' + (summary.minutes === null ? "No time limit" : summary.minutes) + ". " + escapeHtml(summary.message) + "</p>";
  return heading(exam ? "Mock Exam" : "Practice", exam ? "The active exam stays answer-only until you submit or time expires." : "Practice reveals feedback and Arabic guidance after each submitted response.") + '<section class="panel"><form data-setup="' + mode + '"><div class="setup-grid"><label class="field"><span>Module</span><select name="moduleId">' + select(app.data.modules, values.moduleId, "modules") + '</select></label><label class="field"><span>Lesson</span><select name="lessonId">' + select(app.data.lessons, values.lessonId, "lessons") + '</select></label><label class="field"><span>Topic</span><select name="topic"><option value="all">All topics</option>' + topics.map(function (topic) { return '<option value="' + escapeHtml(topic) + '"' + selected(values.topic, topic) + '>' + escapeHtml(topic) + "</option>"; }).join("") + '</select></label><label class="field"><span>Type</span><select name="type"><option value="all">All types</option><option value="mcq"' + selected(values.type, "mcq") + '>Multiple choice</option><option value="true-false"' + selected(values.type, "true-false") + '>True / False</option></select></label><label class="field"><span>Difficulty</span><select name="difficulty"><option value="all">All difficulty</option><option value="easy"' + selected(values.difficulty, "easy") + '>Easy</option><option value="medium"' + selected(values.difficulty, "medium") + '>Medium</option><option value="hard"' + selected(values.difficulty, "hard") + '>Hard</option></select></label><label class="field"><span>Bloom</span><select name="bloomLevel"><option value="all">All levels</option><option value="remember"' + selected(values.bloomLevel, "remember") + '>Remember</option><option value="apply"' + selected(values.bloomLevel, "apply") + '>Apply</option><option value="analyze"' + selected(values.bloomLevel, "analyze") + '>Analyze</option></select></label><label class="field"><span>Question count</span><input name="count" type="number" min="1" max="' + app.data.questions.length + '" value="' + escapeHtml(values.count) + '" /></label>' + (exam ? '<label class="field"><span>Minutes</span><input name="minutes" type="number" min="1" max="180" value="' + escapeHtml(values.minutes) + '" /></label>' : "") + '<label class="field"><span>Order</span><select name="order"><option value="original"' + selected(values.order, "original") + '>Original order</option><option value="random"' + selected(values.order, "random") + '>Random order</option></select></label></div>' + summaryText + '<div class="action-row"><button class="btn btn--primary" type="submit"' + (summary.canStart ? "" : " disabled") + '>Start ' + (exam ? "Mock Exam" : "Practice") + "</button></div></form></section>";
}
function practiceOptions(question, selected, locked) {
  const selectedValue = selected === true ? "true" : selected === false ? "false" : selected === undefined ? "" : String(selected);
  const choices = question.type === "mcq" ? question.options.map(function (text, index) { return { value: String(index), marker: index + 1, text: text }; }) : [{ value: "true", marker: "T", text: "True" }, { value: "false", marker: "F", text: "False" }];
  return choices.map(function (choice) { return '<label class="answer-row"><input type="radio" name="response" value="' + escapeHtml(choice.value) + '"' + (choice.value === selectedValue ? " checked" : "") + (locked ? " disabled" : " required") + ' /><span class="answer-marker">' + escapeHtml(choice.marker) + '</span><span class="answer-copy">' + escapeHtml(choice.text) + "</span></label>"; }).join("");
}
function practiceFeedback(feedback) {
  const explanation = feedback.explanation;
  return '<section class="feedback ' + (feedback.correct ? "correct" : "wrong") + '"><strong>' + (feedback.correct ? "Correct ✓" : "Wrong ✕") + (feedback.scored ? "" : " — unscored") + "</strong><p>" + escapeHtml(feedback.rationale || "No rationale is available.") + "</p>" + citation(feedback.sourceRefs) + (explanation ? '<div class="guidance-panel arabic" lang="ar" dir="rtl"><h3>إرشاد دراسي مولد</h3><p>' + escapeHtml(explanation.translation) + "</p>" + explanation.explanation.map(function (paragraph) { return "<p>" + escapeHtml(paragraph) + "</p>"; }).join("") + "<p><strong>ملاحظة مراجعة:</strong> " + escapeHtml(explanation.note) + "</p></div>" : "") + "</section>";
}
export function renderPractice() {
  if (app.practiceResult) return renderPracticeResult();
  if (!app.practice || app.practice.status !== "active") return setupScope("practice");
  const question = app.data.questionById[app.practice.questionIds[app.practice.index]];
  if (!question) return renderNotFound("The active practice question is unavailable.");
  const view = getPracticeQuestionView(app.practice, question, app.data.explanationByQuestionId[question.id]);
  const feedback = view.feedback;
  const navigator = app.practice.questionIds.map(function (id, index) { return '<button class="' + (index === app.practice.index ? "current " : "") + (app.practice.answers[id] ? "answered" : "") + '" data-action="practice-index" data-index="' + index + '" aria-label="Question ' + (index + 1) + '">' + (index + 1) + "</button>"; }).join("");
  return heading("Practice", "Immediate feedback is available after you submit an answer.") + '<section class="session-layout"><div class="question-workspace"><div class="session-progress"><span>Question ' + (app.practice.index + 1) + " of " + app.practice.questionIds.length + "</span><strong>" + Math.round((app.practice.index + 1) * 100 / app.practice.questionIds.length) + '%</strong></div><div class="progress-track"><span style="--value:' + ((app.practice.index + 1) * 100 / app.practice.questionIds.length) + '%"></span></div>' + questionMeta(question) + '<p class="session-prompt" lang="en" dir="ltr">' + escapeHtml(question.prompt) + '</p><form class="answer-form" data-answer="practice">' + practiceOptions(question, view.response, view.locked) + '<button class="btn btn--primary" type="submit"' + (view.locked ? " disabled" : "") + ">" + (view.locked ? "Answer checked" : "Check answer") + "</button></form>" + (feedback ? practiceFeedback(feedback) : "") + '<p class="keyboard-hint">Keyboard: 1–4 select · T/F true or false · B bookmark · S skip · ←/→ navigate.</p><div class="session-actions"><button class="btn" data-action="practice-prev">Previous</button><button class="btn" data-action="practice-skip">Skip</button><button class="btn" data-action="bookmark-current">Bookmark</button><button class="btn btn--primary" data-action="practice-next">Next</button><button class="btn" data-action="finish-practice">Finish</button></div></div><aside class="session-rail"><h2>Session overview</h2><p class="status success">Answered ' + Object.keys(app.practice.answers).length + '</p><p class="status">Current ' + (app.practice.index + 1) + '</p><h3>Question navigator</h3><div class="navigator">' + navigator + "</div></aside></section>";
}
function renderPracticeResult() {
  const result = app.practiceResult;
  return heading("Practice complete", "Your scoreable attempts have been saved to revision and mistakes.") + '<section class="panel"><div class="revision-grid"><div><span class="metric-label">Answered</span><strong class="summary-value">' + result.answered + '</strong></div><div><span class="metric-label">Correct</span><strong class="summary-value">' + result.correct + '</strong></div><div><span class="metric-label">Wrong</span><strong class="summary-value">' + result.incorrect + '</strong></div><div><span class="metric-label">Accuracy</span><strong class="summary-value">' + result.accuracy + '%</strong></div></div><div class="action-row"><a class="btn btn--primary" href="#/practice" data-action="new-practice">Try another Practice</a><a class="btn" href="#/revision">Open Revision</a><a class="btn" href="#/mistakes">Review Mistakes</a></div></section>';
}

export function renderExam() {
  if (app.examResult) return renderExamResult();
  if (!app.exam && app.state.activeExam && app.state.activeExam.status === "active") { app.exam = hydrateExam(app.state.activeExam, app.data.questions, app.data.explanations); startTimer(); }
  return app.exam && app.exam.status === "active" ? renderActiveExam() : setupScope("exam");
}
function renderActiveExam() {
  const current = app.data.questionById[app.exam.questionIds[app.exam.index]];
  if (!current) return renderNotFound("The active Mock Exam question is unavailable.");
  const count = app.exam.questionIds.length;
  const nav = app.exam.questionIds.map(function (id, index) {
    return '<button class="' + (index === app.exam.index ? "current " : "") + (app.exam.answers[id] ? "answered " : "") + (app.exam.flagged.includes(id) ? "flagged" : "") + '" data-action="exam-index" data-index="' + index + '" aria-label="Question ' + (index + 1) + '">' + (index + 1) + "</button>";
  }).join("");
  return heading("Mock Exam", "Your answers are scored only after you submit.") + '<section class="session-layout"><div class="question-workspace"><div class="session-progress"><span>Question ' + (app.exam.index + 1) + " of " + count + '</span><strong class="timer">' + formatSeconds(getExamRemainingSeconds(app.exam)) + '</strong></div><div class="progress-track"><span style="--value:' + ((app.exam.index + 1) * 100 / count) + '%"></span></div><p class="session-prompt" lang="en" dir="ltr">' + escapeHtml(current.prompt) + '</p><form class="answer-form" data-answer="exam">' + examOptions(current, app.exam.answers[current.id] && app.exam.answers[current.id].response) + '<button class="btn btn--primary" type="submit">Save answer</button></form><div class="session-actions"><button class="btn" data-action="exam-prev">Previous</button><button class="btn" data-action="exam-flag">Flag question</button><button class="btn" data-action="exam-bookmark">Bookmark</button><button class="btn btn--primary" data-action="exam-next">Next</button><button class="btn btn--danger" data-action="confirm-submit-exam">Submit</button></div></div><aside class="session-rail"><h2>Exam navigator</h2><p class="status">Answered ' + Object.keys(app.exam.answers).length + '</p><p class="status warning">Flagged ' + app.exam.flagged.length + '</p><div class="navigator">' + nav + "</div></aside></section>";
}
function examOptions(question, selected) {
  const selectedValue = selected === true ? "true" : selected === false ? "false" : selected === undefined ? "" : String(selected);
  const choices = question.type === "mcq" ? question.options.map(function (text, index) { return { value: String(index), marker: index + 1, text: text }; }) : [{ value: "true", marker: "T", text: "True" }, { value: "false", marker: "F", text: "False" }];
  return choices.map(function (choice) { return '<label class="answer-row"><input type="radio" name="response" value="' + escapeHtml(choice.value) + '"' + (choice.value === selectedValue ? " checked" : "") + ' /><span class="answer-marker">' + escapeHtml(choice.marker) + '</span><span class="answer-copy">' + escapeHtml(choice.text) + "</span></label>"; }).join("");
}
function renderExamResult() {
  const result = app.examResult;
  return heading("Mock Exam results", "Answers, rationales, and bilingual guidance are now available to review.") + '<section class="panel"><div class="revision-grid"><div><span class="metric-label">Scoreable</span><strong class="summary-value">' + result.summary.scoreable + '</strong></div><div><span class="metric-label">Correct</span><strong class="summary-value">' + result.summary.correct + '</strong></div><div><span class="metric-label">Incorrect</span><strong class="summary-value">' + result.summary.incorrect + '</strong></div><div><span class="metric-label">Unanswered</span><strong class="summary-value">' + result.summary.unanswered + '</strong></div><div><span class="metric-label">Percentage</span><strong class="summary-value">' + result.summary.percentage + '%</strong></div><div><span class="metric-label">Duration</span><strong class="summary-value">' + formatSeconds(result.summary.durationSeconds) + "</strong></div></div></section><section class=\"panel\"><div class=\"section-title\"><h2>Question review</h2></div>" + result.reviews.map(function (review, index) {
    const question = app.data.questionById[review.questionId];
    const arabic = review.explanation;
    return '<article class="question-card"><span class="status ' + (review.correct ? "success" : review.correct === false ? "error" : "warning") + '">' + (review.correct ? "Correct" : review.correct === false ? "Incorrect" : "Unanswered or unscored") + "</span><h2>" + (index + 1) + ". " + escapeHtml(question.prompt) + "</h2><p><strong>Rationale:</strong> " + escapeHtml(review.rationale || "No rationale is available.") + "</p>" + citation(review.sourceRefs) + (arabic ? '<div class="guidance-panel arabic" lang="ar" dir="rtl"><p>' + escapeHtml(arabic.translation) + "</p>" + arabic.explanation.map(function (paragraph) { return "<p>" + escapeHtml(paragraph) + "</p>"; }).join("") + "<p>" + escapeHtml(arabic.note) + "</p></div>" : "") + "</article>";
  }).join("") + "</section>";
}

export function renderRevision() {
  const summary = getRevisionSummary(app.data, app.state);
  const weak = summary.weakModules.concat(summary.weakTopics);
  return heading("Revision", "Use scoreable results to choose your next revision pass.") + '<section class="panel"><div class="revision-grid"><div><span class="metric-label">Completed lessons</span><strong class="summary-value">' + summary.lessons.completed + "/" + summary.lessons.total + '</strong></div><div><span class="metric-label">Answered</span><strong class="summary-value">' + summary.attempts.answered + '</strong></div><div><span class="metric-label">Correct</span><strong class="summary-value">' + summary.attempts.correct + '</strong></div><div><span class="metric-label">Accuracy</span><strong class="summary-value">' + summary.attempts.accuracy + '%</strong></div><div><span class="metric-label">Mistakes</span><strong class="summary-value">' + summary.mistakeCount + '</strong></div></div></section><section class="panel"><div class="section-title"><h2>Weak modules and topics</h2></div>' + (weak.length ? '<div class="item-list">' + weak.map(function (item) { const module = item.id.startsWith("module-") ? item.id : ""; const topic = module ? "" : item.id; return '<div class="item-row"><span><strong>' + escapeHtml(item.title) + '</strong><small>' + escapeHtml(item.answered) + " scoreable attempts · " + escapeHtml(item.accuracy) + '% accuracy</small></span><button class="btn" data-action="focused-practice" data-module="' + escapeHtml(module) + '" data-topic="' + escapeHtml(topic) + '">Practice this area</button></div>'; }).join("") + "</div>" : '<div class="empty-state"><strong>No weak areas yet.</strong><p>Complete scoreable practice questions to see a focused revision path.</p></div>') + "</section>";
}
export function renderMistakes() {
  const rows = getMistakeQuestions(app.data.questions, app.state);
  return heading("Mistakes", "Questions are ranked by incorrect scoreable attempts, then most recent attempt.") + '<section class="panel">' + (rows.length ? '<div class="item-list">' + rows.map(function (question) { return '<article class="item-row"><span><strong>' + escapeHtml(question.prompt) + '</strong><small>' + escapeHtml(question.mistakeCount) + " incorrect attempt" + (question.mistakeCount === 1 ? "" : "s") + " · " + (question.masteredAfterMistake ? "Mastered after mistake" : "Needs revision") + '</small></span><button class="btn" data-action="focused-practice" data-question="' + escapeHtml(question.id) + '">Practice</button></article>'; }).join("") + "</div>" : '<div class="empty-state"><strong>No mistakes recorded.</strong><p>Incorrect scoreable responses will appear here with a focused Practice action.</p><a class="btn" href="#/practice">Start Practice</a></div>') + "</section>";
}
export function renderBookmarks() {
  const lessons = getBookmarkedLessons(app.data.lessons, app.state);
  const questions = getBookmarkedQuestions(app.data.questions, app.state);
  const lessonRows = lessons.length ? '<div class="item-list">' + lessons.map(function (lesson) { return '<div class="item-row"><span><strong>' + escapeHtml(lesson.title) + '</strong><small>' + escapeHtml((moduleFor(lesson.moduleId) || {}).title || lesson.moduleId) + '</small></span><div class="page-actions"><a class="btn" href="#/lesson/' + escapeHtml(lesson.id) + '">Open</a><button class="btn" data-action="bookmark-lesson" data-lesson="' + escapeHtml(lesson.id) + '">Remove</button></div></div>'; }).join("") + "</div>" : '<p class="muted">No lesson bookmarks. Bookmark a lesson from its material page.</p>';
  const questionRows = questions.length ? '<div class="item-list">' + questions.map(function (question) { return '<div class="item-row"><span><strong>' + escapeHtml(question.prompt) + '</strong><small>' + escapeHtml(question.topic) + '</small></span><div class="page-actions"><button class="btn" data-action="focused-practice" data-question="' + escapeHtml(question.id) + '">Practice</button><button class="btn" data-action="bookmark-question" data-question="' + escapeHtml(question.id) + '">Remove</button></div></div>'; }).join("") + "</div>" : '<p class="muted">No question bookmarks. Save a question from the Question Bank or a session.</p>';
  return heading("Bookmarks", "Saved lessons and questions stay separate so you can revisit either safely.") + '<section class="panel"><div class="section-title"><h2>Lessons</h2></div>' + lessonRows + '</section><section class="panel"><div class="section-title"><h2>Questions</h2></div>' + questionRows + "</section>";
}
export function renderSettings() {
  const theme = document.documentElement.dataset.theme || "light";
  return heading("Settings", "Theme and progress controls are stored only on this device.") + '<section class="settings-panel"><h2>Theme</h2><p class="muted">Current theme: ' + escapeHtml(theme) + '.</p><div class="action-row"><button class="btn" data-action="theme" data-theme="light">Use light theme</button><button class="btn" data-action="theme" data-theme="dark">Use dark theme</button></div></section><section class="settings-panel"><h2>Progress data</h2><p class="muted">Export your local OS Study progress as JSON, or import a valid backup. A failed import leaves your current progress unchanged.</p><div class="action-row"><button class="btn" data-action="export-progress">' + icon("download") + 'Export progress JSON</button><button class="btn" data-action="import-progress">' + icon("upload") + 'Import progress</button><button class="btn btn--danger" data-action="confirm-reset">Reset progress</button></div></section>';
}
function renderNotFound(copy) { return heading("Page not found") + '<section class="state-panel"><h2>' + escapeHtml(copy || "The requested route is unavailable.") + '</h2><p>Use Dashboard to return to the available study routes.</p><a class="btn btn--primary" href="#/dashboard">Go to Dashboard</a></section>'; }

function renderView(route) {
  if (route.name === "lesson") return renderLesson(route);
  if (route.name === "not-found") return renderNotFound();
  const views = { dashboard: renderDashboard, material: renderMaterial, questions: renderQuestions, explanations: renderExplanations, practice: renderPractice, exam: renderExam, revision: renderRevision, mistakes: renderMistakes, bookmarks: renderBookmarks, settings: renderSettings };
  return views[route.name] ? views[route.name]() : renderNotFound();
}
function updateNav(route) {
  document.querySelectorAll("[data-route]").forEach(function (item) {
    item.toggleAttribute("aria-current", item.dataset.route === route.name || route.name === "lesson" && item.dataset.route === "material");
  });
  document.querySelectorAll(".more-menu").forEach(function (menu) { menu.removeAttribute("open"); });
}
function render(options) {
  if (!app.data) return;
  const config = options || {};
  const route = routeFromHash(location.hash || "#/dashboard");
  const main = document.querySelector("#main-content");
  main.innerHTML = renderView(route);
  document.title = (ROUTE_TITLES[route.name] || "Not found") + " · Operating Systems Study";
  updateNav(route);
  if (config.focus !== false) queueMicrotask(function () { const focus = main.querySelector("h1"); if (focus) focus.focus({ preventScroll: true }); });
}
function navigateTo(targetHash) {
  const decision = navigationRenderDecision(location.hash, targetHash);
  if (decision.setHash) location.hash = targetHash;
  if (decision.renderNow) render();
}
function setTheme(theme) {
  const safe = theme === "dark" ? "dark" : "light";
  document.documentElement.dataset.theme = safe;
  localStorage.setItem(THEME_KEY, safe);
  document.querySelectorAll('input[name="theme"]').forEach(function (input) { input.checked = input.value === safe; });
}
function responseFrom(form, question) {
  const value = new FormData(form).get("response");
  if (value === null) return undefined;
  if (question.type === "true-false") return value === "true" ? true : value === "false" ? false : undefined;
  return /^\d+$/.test(String(value)) ? Number(value) : undefined;
}
function startPractice(config) {
  let pool = filterQuestions(app.data.questions, config, app.data);
  if (Array.isArray(config.questionIds)) pool = pool.filter(function (question) { return config.questionIds.includes(question.id); });
  const session = createPracticeSession(pool, Object.assign({}, config, { explanations: app.data.explanations }));
  if (session.status === "empty") { notify(session.emptyReason, true); return; }
  app.practice = session; app.practiceResult = null; navigateTo("#/practice");
}
function startExam(config) {
  const pool = filterQuestions(app.data.questions, config, app.data);
  const exam = createExam(pool, Object.assign({}, config, { course: app.data.course, explanations: app.data.explanations }));
  if (exam.status === "empty") { notify(exam.emptyReason, true); return; }
  app.exam = exam; app.examResult = null; save(setActiveExam(app.state, exam, Date.now(), canonical())); navigateTo("#/exam"); startTimer();
}
function startTimer() {
  clearInterval(app.timer);
  app.timer = setInterval(function () {
    if (!app.exam || app.exam.status !== "active") return;
    if (getExamRemainingSeconds(app.exam) <= 0) { finishExam(true); return; }
    if (routeFromHash(location.hash).name === "exam") render({ focus: false });
  }, 1000);
}
function persistPractice(previous, next) {
  const id = previous.questionIds[previous.index];
  const answer = next.answers[id];
  if (previous.answers[id] || !answer || !answer.scored) return;
  save(recordAttempt(app.state, { questionId: id, response: answer.response, scored: true, finalized: true, correct: answer.correct, at: answer.answeredAt }, answer.answeredAt, canonical()));
}
function finishPractice() {
  if (!app.practice) return;
  const answers = Object.values(app.practice.answers);
  const scored = answers.filter(function (answer) { return answer.scored; });
  const correct = scored.filter(function (answer) { return answer.correct; }).length;
  const summary = { id: app.practice.id, mode: "practice", finishedAt: new Date().toISOString(), scoreable: scored.length, correct: correct, incorrect: scored.length - correct, unanswered: app.practice.questionIds.length - answers.length, percentage: scored.length ? Math.round(correct * 100 / scored.length) : 0, durationSeconds: Math.floor((Date.now() - app.practice.startedAt) / 1000) };
  save(recordSessionSummary(app.state, summary, Date.now(), canonical()));
  app.practiceResult = { answered: answers.length, correct: correct, incorrect: scored.length - correct, accuracy: summary.percentage };
  app.practice = null; render();
}
function finishExam(expired) {
  if (!app.exam) return;
  const result = submitExam(app.exam, { questions: app.data.questions, explanations: app.data.explanations, now: Date.now() });
  result.reviews.forEach(function (review) {
    if (review.scored && review.answeredAt) save(recordAttempt(app.state, { questionId: review.questionId, response: review.response, scored: true, finalized: true, correct: review.correct, at: review.answeredAt }, review.answeredAt, canonical()));
  });
  const summary = { id: result.id, mode: "exam", finishedAt: new Date(result.submittedAt).toISOString(), scoreable: result.summary.scoreable, correct: result.summary.correct, incorrect: result.summary.incorrect, unanswered: result.summary.unanswered, percentage: result.summary.percentage, durationSeconds: result.summary.durationSeconds };
  save(recordSessionSummary(clearActiveExam(app.state, Date.now(), canonical()), summary, Date.now(), canonical()));
  app.exam = null; app.examResult = result; clearInterval(app.timer);
  if (expired) notify("Time expired. Your Mock Exam was submitted.");
  render();
}
function dialog(title, description, label, action) {
  app.focusReturn = document.activeElement;
  const root = document.querySelector("#dialog-root");
  root.innerHTML = '<div class="dialog-backdrop"><section class="dialog" role="dialog" aria-modal="true" aria-labelledby="dialog-title" aria-describedby="dialog-description"><h2 id="dialog-title">' + escapeHtml(title) + '</h2><p id="dialog-description">' + escapeHtml(description) + '</p><div class="action-row"><button class="btn" data-action="close-dialog">Cancel</button><button class="btn btn--danger" data-action="' + escapeHtml(action) + '">' + escapeHtml(label) + "</button></div></section></div>";
  queueMicrotask(function () { const button = root.querySelector('[data-action="' + action + '"]'); if (button) button.focus(); });
}
function closeDialog() {
  document.querySelector("#dialog-root").replaceChildren();
  if (app.focusReturn && app.focusReturn.focus) app.focusReturn.focus({ preventScroll: true });
  app.focusReturn = null;
}
function focusableDialogControls() {
  const dialogElement = document.querySelector("#dialog-root .dialog");
  return dialogElement ? Array.from(dialogElement.querySelectorAll("button:not([disabled]), [href], input:not([disabled]), select:not([disabled]), textarea:not([disabled]), [tabindex]:not([tabindex='-1'])")) : [];
}
function bookmark(kind, id) { save(toggleBookmark(app.state, kind, id, Date.now(), canonical())); notify("Bookmark updated."); }

function handleAction(event) {
  const button = event.target.closest("[data-action]");
  if (!button) return;
  const data = button.dataset;
  if (data.action === "retry-load") { location.reload(); return; }
  if (data.action === "reset-filters") { app.filters[data.kind] = emptyFilters(); app.pages[data.kind] = 1; render(); return; }
  if (data.action === "page") { app.pages[data.kind] = Math.max(1, Number(data.page)); render({ focus: false }); return; }
  if (data.action === "reveal-answer") { app.revealed.has(data.question) ? app.revealed.delete(data.question) : app.revealed.add(data.question); render({ focus: false }); return; }
  if (data.action === "bookmark-question") { bookmark("question", data.question); render({ focus: false }); return; }
  if (data.action === "bookmark-lesson") { bookmark("lesson", data.lesson); render({ focus: false }); return; }
  if (data.action === "toggle-complete") { const value = app.state.lessonProgress[data.lesson] && app.state.lessonProgress[data.lesson].status === "completed" ? "in-progress" : "completed"; save(markLessonComplete(app.state, data.lesson, value, Date.now(), canonical())); notify(value === "completed" ? "Lesson marked completed." : "Lesson marked in progress."); render({ focus: false }); return; }
  if (data.action === "practice-lesson") { startPractice({ lessonId: data.lesson, count: 10, order: "original" }); return; }
  if (data.action === "focused-practice") { startPractice({ questionIds: data.question ? [data.question] : undefined, moduleId: data.module || "all", topic: data.topic || "all", count: data.question ? 1 : 10, order: "original" }); return; }
  if (data.action === "practice-prev") { app.practice = movePracticeQuestion(app.practice, -1); render({ focus: false }); return; }
  if (data.action === "practice-next" || data.action === "practice-skip") { app.practice = movePracticeQuestion(app.practice, 1); render({ focus: false }); return; }
  if (data.action === "practice-index") { app.practice = goToPracticeQuestion(app.practice, Number(data.index)); render({ focus: false }); return; }
  if (data.action === "bookmark-current") { bookmark("question", app.practice.questionIds[app.practice.index]); render({ focus: false }); return; }
  if (data.action === "finish-practice") { finishPractice(); return; }
  if (data.action === "new-practice") { app.practiceResult = null; navigateTo("#/practice"); return; }
  if (data.action === "exam-prev") { app.exam = moveExamQuestion(app.exam, -1); save(setActiveExam(app.state, app.exam, Date.now(), canonical())); render({ focus: false }); return; }
  if (data.action === "exam-next") { app.exam = moveExamQuestion(app.exam, 1); save(setActiveExam(app.state, app.exam, Date.now(), canonical())); render({ focus: false }); return; }
  if (data.action === "exam-index") { app.exam = goToExamQuestion(app.exam, Number(data.index)); save(setActiveExam(app.state, app.exam, Date.now(), canonical())); render({ focus: false }); return; }
  if (data.action === "exam-flag") { app.exam = toggleExamFlag(app.exam, app.exam.questionIds[app.exam.index]); save(setActiveExam(app.state, app.exam, Date.now(), canonical())); render({ focus: false }); return; }
  if (data.action === "exam-bookmark") { app.exam = toggleExamBookmark(app.exam, app.exam.questionIds[app.exam.index]); save(setActiveExam(app.state, app.exam, Date.now(), canonical())); bookmark("question", app.exam.questionIds[app.exam.index]); render({ focus: false }); return; }
  if (data.action === "confirm-submit-exam") { dialog("Submit Mock Exam?", "You cannot return to the active exam after submission. Results then reveal feedback and guidance.", "Submit exam", "submit-exam"); return; }
  if (data.action === "submit-exam") { closeDialog(); finishExam(false); return; }
  if (data.action === "close-dialog") { closeDialog(); return; }
  if (data.action === "confirm-reset") { dialog("Reset OS Study progress?", "This removes only local OS Study progress and theme preference from this browser.", "Reset progress", "reset-progress"); return; }
  if (data.action === "reset-progress") { app.state = resetState(undefined, Date.now()); localStorage.removeItem(THEME_KEY); app.practice = null; app.exam = null; app.practiceResult = null; app.examResult = null; closeDialog(); setTheme("light"); notify("OS Study progress was reset."); render(); return; }
  if (data.action === "export-progress") { const blob = new Blob([exportState(app.state, canonical())], { type: "application/json" }); const url = URL.createObjectURL(blob); const link = document.createElement("a"); link.href = url; link.download = "os-study-progress.json"; link.click(); URL.revokeObjectURL(url); notify("Progress export downloaded."); return; }
  if (data.action === "import-progress") { document.querySelector("#progress-import").click(); return; }
  if (data.action === "theme") { setTheme(data.theme); notify("Theme changed to " + data.theme + "."); render({ focus: false }); }
}
function handleSubmit(event) {
  const form = event.target;
  if (!(form instanceof HTMLFormElement)) return;
  if (form.dataset.filterForm) { event.preventDefault(); app.filters[form.dataset.filterForm] = Object.assign({}, app.filters[form.dataset.filterForm], Object.fromEntries(new FormData(form).entries())); app.pages[form.dataset.filterForm] = 1; render({ focus: false }); return; }
  if (form.dataset.setup) {
    event.preventDefault();
    const mode = form.dataset.setup;
    const values = Object.assign({}, setupValues(mode), Object.fromEntries(new FormData(form).entries()));
    app.setups[mode] = values;
    const summary = getSetupSummary(mode, app.data.questions, values, app.data.course, app.data);
    if (!summary.canStart) { notify(summary.message, true); render({ focus: false }); return; }
    const config = Object.assign({}, values, { count: summary.requestedCount, minutes: summary.minutes });
    mode === "practice" ? startPractice(config) : startExam(config);
    return;
  }
  if (form.dataset.answer === "practice" && app.practice) { event.preventDefault(); const question = app.data.questionById[app.practice.questionIds[app.practice.index]]; if (app.practice.answers[question.id]) { notify("This Practice answer is already locked."); render({ focus: false }); return; } const response = responseFrom(form, question); if (response === undefined) { notify("Choose an answer before checking it.", true); return; } const previous = app.practice; app.practice = answerPracticeQuestion(previous, response); persistPractice(previous, app.practice); render({ focus: false }); return; }
  if (form.dataset.answer === "exam" && app.exam) { event.preventDefault(); const question = app.data.questionById[app.exam.questionIds[app.exam.index]]; const response = responseFrom(form, question); if (response === undefined) { notify("Choose an answer before saving it.", true); return; } app.exam = answerExamQuestion(app.exam, response); save(setActiveExam(app.state, app.exam, Date.now(), canonical())); notify("Answer saved."); render({ focus: false }); }
}
function handleChange(event) {
  const setup = event.target.closest("form[data-setup]");
  if (setup) {
    const mode = setup.dataset.setup;
    app.setups[mode] = Object.assign({}, setupValues(mode), Object.fromEntries(new FormData(setup).entries()));
    render({ focus: false });
    return;
  }
  const form = event.target.closest("form[data-filter-form]");
  if (!form) return;
  const kind = form.dataset.filterForm;
  app.filters[kind] = Object.assign({}, app.filters[kind], Object.fromEntries(new FormData(form).entries()));
  app.pages[kind] = 1;
  render({ focus: false });
}
function handleShortcut(event) {
  if (!shouldHandleShortcut(event)) return;
  const mode = app.practice && app.practice.status === "active" ? "practice" : app.exam && app.exam.status === "active" ? "exam" : "";
  if (!mode) return;
  event.preventDefault();
  const session = mode === "practice" ? app.practice : app.exam;
  const question = app.data.questionById[session.questionIds[session.index]];
  const response = /^[1-4]$/.test(event.key) ? Number(event.key) - 1 : /^t$/i.test(event.key) ? true : /^f$/i.test(event.key) ? false : undefined;
  if (response !== undefined) {
    if (mode === "practice" && !app.practice.answers[question.id]) { const before = app.practice; app.practice = answerPracticeQuestion(before, response); persistPractice(before, app.practice); }
    else app.exam = answerExamQuestion(app.exam, response);
  }
  if (event.key === "ArrowLeft") mode === "practice" ? app.practice = movePracticeQuestion(app.practice, -1) : app.exam = moveExamQuestion(app.exam, -1);
  if (event.key === "ArrowRight" || /^s$/i.test(event.key)) mode === "practice" ? app.practice = movePracticeQuestion(app.practice, 1) : app.exam = moveExamQuestion(app.exam, 1);
  if (/^b$/i.test(event.key)) bookmark("question", question.id);
  if (mode === "exam") save(setActiveExam(app.state, app.exam, Date.now(), canonical()));
  render({ focus: false });
}
async function importProgress(file) {
  try { save(importState(await file.text(), canonical())); notify("Progress imported successfully."); render(); }
  catch (error) { notify(error && error.message || "The selected progress file is not valid.", true); }
}
async function bootstrap() {
  document.querySelectorAll("[data-icon]").forEach(function (slot) { slot.innerHTML = icon(slot.dataset.icon); });
  setTheme(localStorage.getItem(THEME_KEY) === "dark" ? "dark" : "light");
  document.querySelectorAll('input[name="theme"]').forEach(function (input) { input.addEventListener("change", function () { setTheme(input.value); }); });
  document.addEventListener("click", handleAction);
  document.addEventListener("submit", handleSubmit);
  document.addEventListener("change", handleChange);
  document.addEventListener("keydown", function (event) {
    if (document.querySelector("#dialog-root").children.length) {
      if (event.key === "Tab" && trapDialogFocus(event, focusableDialogControls())) return;
      if (event.key === "Escape") { event.preventDefault(); closeDialog(); return; }
    }
    handleShortcut(event);
  });
  document.querySelector("#progress-import").addEventListener("change", function (event) { const file = event.target.files && event.target.files[0]; if (file) importProgress(file); event.target.value = ""; });
  addEventListener("hashchange", function () { render(); });
  try {
    app.data = await loadCourseData();
    app.state = loadState(undefined, Date.now(), canonical());
    if (localStorage.getItem(BACKUP_STORAGE_KEY)) notify("A previous progress value was backed up and reset because it was not usable for this OS Study version.");
    if (!location.hash) location.hash = "#/dashboard"; else render();
  } catch (error) {
    document.querySelector("#main-content").innerHTML = '<section id="app-error" class="state-panel"><h1>Unable to load Operating Systems Study</h1><p>' + escapeHtml(error && error.message || "Course data could not be loaded.") + '</p><div class="action-row"><button class="btn btn--primary" data-action="retry-load">Retry</button><a class="btn" href="#/dashboard">Dashboard</a></div></section>';
  }
}
if (typeof document !== "undefined") bootstrap();
