#!/usr/bin/env node
/*
 * Direct browser QA for the static Operating Systems Study site.
 *
 * Requires the bundled Playwright runtime via NODE_PATH. It deliberately uses
 * a fresh browser context and only exercises visible UI flows.
 */
import assert from "node:assert/strict";
import { createRequire } from "node:module";
import { mkdtemp, mkdir, readFile } from "node:fs/promises";
import { existsSync } from "node:fs";
import { fileURLToPath } from "node:url";
import { dirname, join, resolve } from "node:path";
import { spawn } from "node:child_process";
import { tmpdir } from "node:os";

import {
  assertBrowserHealth,
  terminateStartedChild,
  waitForReadinessWithCleanup,
} from "./browser-check-helpers.mjs";

const require = createRequire(import.meta.url);
const { chromium } = require("playwright");
const scriptDirectory = dirname(fileURLToPath(import.meta.url));
const repositoryRoot = resolve(scriptDirectory, "..", "..");
const studyDirectory = resolve(scriptDirectory, "..");
const defaultBaseUrl = "http://127.0.0.1:8000/";
const baseUrl = process.env.OS_STUDY_BASE_URL || defaultBaseUrl;
const customScreenshotDirectory = process.env.OS_QA_SCREENSHOT_DIR;
const measurements = [];
const screenshots = [];
const browserEvents = { pageErrors: [], console: [], failedRequests: [], essentialDataFailures: [] };

function installedChromiumExecutable() {
  const candidates = [
    process.env.OS_STUDY_CHROMIUM_EXECUTABLE,
    "C:\\Program Files\\Google\\Chrome\\Application\\chrome.exe",
    "C:\\Program Files (x86)\\Google\\Chrome\\Application\\chrome.exe",
    "C:\\Program Files\\Microsoft\\Edge\\Application\\msedge.exe",
    "C:\\Program Files (x86)\\Microsoft\\Edge\\Application\\msedge.exe",
  ].filter(Boolean);
  return candidates.find((candidate) => existsSync(candidate)) || null;
}

async function launchBrowser() {
  try {
    const browser = await chromium.launch({ headless: true });
    pass("browser runtime", "bundled Playwright Chromium");
    return browser;
  } catch (bundledError) {
    const executablePath = installedChromiumExecutable();
    if (!executablePath) {
      throw new Error(`Bundled Playwright Chromium is unavailable and no installed Chromium executable was found. ${bundledError.message}`);
    }
    const browser = await chromium.launch({ headless: true, executablePath });
    pass("browser runtime", `bundled Playwright Chromium unavailable; using installed local Chromium executable ${executablePath}`);
    return browser;
  }
}

function pass(name, detail) {
  measurements.push({ name, detail });
  console.log(`PASS ${name}: ${detail}`);
}

function applicationUrl(route) {
  return `${baseUrl.replace(/\/$/, "")}/#/${route}`;
}

function delay(milliseconds) {
  return new Promise((resolveDelay) => setTimeout(resolveDelay, milliseconds));
}

async function isStudySite(url) {
  try {
    const response = await fetch(url, { signal: AbortSignal.timeout(800) });
    if (!response.ok) return false;
    const body = await response.text();
    return body.includes("<title>Operating Systems Study</title>") && body.includes("./js/app.js");
  } catch {
    return false;
  }
}

async function waitForStudySite(url, child) {
  const deadline = Date.now() + 15_000;
  while (Date.now() < deadline) {
    if (await isStudySite(url)) return;
    if (child?.exitCode !== null) throw new Error(`The QA server exited before it became ready (exit ${child.exitCode}).`);
    await delay(150);
  }
  throw new Error(`Timed out waiting for the Operating Systems Study app at ${url}.`);
}

async function ensureServer() {
  if (await isStudySite(baseUrl)) {
    pass("server", `using existing Operating Systems Study server at ${baseUrl}`);
    return null;
  }
  if (baseUrl !== defaultBaseUrl) {
    throw new Error(`OS_STUDY_BASE_URL is not serving the expected Operating Systems Study app: ${baseUrl}`);
  }
  const server = spawn("python", ["-m", "http.server", "8000", "--directory", "study-website"], {
    cwd: repositoryRoot,
    stdio: ["ignore", "pipe", "pipe"],
    windowsHide: true,
  });
  let serverError = "";
  server.stderr.on("data", (chunk) => { serverError += chunk.toString(); });
  server.on("error", (error) => { serverError += error.message; });
  try {
    await waitForReadinessWithCleanup(server, () => waitForStudySite(baseUrl, server));
  } catch (error) {
    throw new Error(`${error.message}${serverError ? ` Server output: ${serverError.trim()}` : ""}`);
  }
  pass("server", `started Python static server at ${baseUrl}`);
  return server;
}

async function stopServer(server) {
  await terminateStartedChild(server);
}

async function pngSize(file) {
  const bytes = await readFile(file);
  assert.equal(bytes.subarray(1, 4).toString("ascii"), "PNG", `${file} must be a PNG image`);
  return { width: bytes.readUInt32BE(16), height: bytes.readUInt32BE(20) };
}

async function createScreenshotDirectory() {
  if (customScreenshotDirectory) {
    const directory = resolve(customScreenshotDirectory);
    await mkdir(directory, { recursive: true });
    return directory;
  }
  return mkdtemp(join(tmpdir(), "os-study-qa-"));
}

function attachEventCollection(page) {
  page.on("pageerror", (error) => browserEvents.pageErrors.push(error.message));
  page.on("console", (message) => {
    if (["error", "warning"].includes(message.type())) browserEvents.console.push({ type: message.type(), text: message.text() });
  });
  page.on("requestfailed", (request) => browserEvents.failedRequests.push(`${request.method()} ${request.url()} (${request.failure()?.errorText || "unknown failure"})`));
  page.on("response", (response) => {
    if (response.url().includes("/data/") && !response.ok()) browserEvents.essentialDataFailures.push(`${response.status()} ${response.url()}`);
  });
}

async function waitForView(page, heading) {
  await page.getByRole("heading", { level: 1, name: heading }).waitFor({ state: "visible", timeout: 12_000 });
  await page.waitForFunction(() => !document.querySelector("#app-loading"), undefined, { timeout: 12_000 });
}

async function go(page, route, heading) {
  await page.goto(applicationUrl(route), { waitUntil: "networkidle" });
  await waitForView(page, heading);
}

async function capture(page, directory, name, options = {}) {
  await page.locator("#toast-region .toast").waitFor({ state: "hidden", timeout: 5_000 });
  await page.evaluate(() => window.scrollTo({ top: 0, left: 0, behavior: "instant" }));
  await page.waitForFunction(() => window.scrollY === 0 && window.scrollX === 0);
  await page.evaluate(() => document.activeElement?.blur());
  const skipLinkIsHidden = await page.locator(".skip-link").evaluate((link) => {
    const bounds = link.getBoundingClientRect();
    return document.activeElement !== link && !link.matches(":focus") && bounds.bottom <= 0;
  });
  assert.ok(skipLinkIsHidden, "clean screenshot capture must hide the skip link before capture");
  const file = join(directory, name);
  await page.screenshot({ path: file, fullPage: Boolean(options.fullPage) });
  const size = await pngSize(file);
  screenshots.push({ name, file, ...size });
  pass("screenshot", `${name} ${size.width}x${size.height} ${file}`);
}

async function metricText(page, label) {
  const entries = await page.locator(".metric-strip > div").allTextContents();
  return entries.find((entry) => entry.includes(label)) || "";
}

async function revisionMetric(page, label) {
  const entries = await page.locator(".revision-grid > div").allTextContents();
  return entries.find((entry) => entry.startsWith(label)) || "";
}

function exportedProgressSummary(exported) {
  const questions = Object.values(exported.questionProgress);
  return {
    projectId: exported.projectId,
    completedLessons: Object.values(exported.lessonProgress)
      .filter((lesson) => lesson.status === "completed").length,
    answered: questions.reduce((total, question) => total + question.attempts, 0),
    correct: questions.reduce((total, question) => total + question.correctAttempts, 0),
    incorrect: questions.reduce((total, question) => total + question.incorrectAttempts, 0),
  };
}

async function assertRevisionProgress(page, summary) {
  assert.match(await revisionMetric(page, "Completed lessons"), new RegExp(`Completed lessons\\s*${summary.completedLessons}/21`));
  assert.match(await revisionMetric(page, "Answered"), new RegExp(`Answered\\s*${summary.answered}`));
  assert.match(await revisionMetric(page, "Correct"), new RegExp(`Correct\\s*${summary.correct}`));
  assert.match(await revisionMetric(page, "Mistakes"), new RegExp(`Mistakes\\s*${summary.incorrect}`));
}

async function setSetupValue(page, mode, name, value) {
  const field = page.locator(`form[data-setup="${mode}"] [name="${name}"]`);
  const tagName = await field.evaluate((element) => element.tagName);
  if (tagName === "SELECT") {
    await field.selectOption(value);
  } else {
    await field.fill(String(value));
    await field.press("Tab");
  }
  await page.locator(`form[data-setup="${mode}"]`).waitFor({ state: "visible" });
}

async function answerPractice(page, optionIndex) {
  const rows = page.locator('form[data-answer="practice"] .answer-row');
  const count = await rows.count();
  assert.ok(count === 2 || count === 4, `Practice must expose typed True/False or MCQ choices, got ${count}.`);
  await rows.nth(optionIndex % count).click();
  await page.getByRole("button", { name: "Check answer" }).click();
  const feedback = page.locator(".feedback");
  await feedback.waitFor({ state: "visible" });
  return feedback.textContent();
}

async function assertMobileLayout(page) {
  const layout = await page.evaluate(() => {
    const nav = document.querySelector("#mobile-navigation")?.getBoundingClientRect();
    const rtl = document.querySelector('[dir="rtl"]')?.getBoundingClientRect();
    const targets = [...document.querySelectorAll("button, .mobile-navigation a, .mobile-navigation summary")]
      .filter((item) => {
        const rect = item.getBoundingClientRect();
        const style = getComputedStyle(item);
        return rect.width > 0 && rect.height > 0 && style.visibility !== "hidden";
      })
      .map((item) => ({ text: item.textContent.trim(), height: item.getBoundingClientRect().height }));
    return {
      scrollWidth: document.documentElement.scrollWidth,
      clientWidth: document.documentElement.clientWidth,
      nav: nav && { left: nav.left, right: nav.right, bottom: nav.bottom, height: nav.height },
      rtl: rtl && { width: rtl.width, height: rtl.height },
      undersized: targets.filter((target) => target.height < 44).slice(0, 10),
      viewportHeight: window.innerHeight,
    };
  });
  assert.ok(layout.scrollWidth <= layout.clientWidth, `mobile horizontal overflow: ${layout.scrollWidth} > ${layout.clientWidth}`);
  assert.ok(layout.nav && layout.nav.left >= 0 && layout.nav.right <= layout.clientWidth + 1 && Math.abs(layout.nav.bottom - layout.viewportHeight) <= 1, "mobile navigation is clipped or not fixed to the viewport");
  assert.ok(layout.rtl && layout.rtl.width > 0 && layout.rtl.height > 0, "Arabic RTL guidance is not visibly rendered on mobile");
  assert.deepEqual(layout.undersized, [], `visible mobile targets below 44px: ${JSON.stringify(layout.undersized)}`);
  pass("mobile layout", `390px viewport, no horizontal overflow, fixed navigation, ${layout.rtl.width}px RTL region, 44px targets`);
}

async function assertIntermediateTouchTargets(page) {
  const targets = await page.locator(".navigator button").evaluateAll((items) => items.map((item) => item.getBoundingClientRect().height));
  assert.ok(targets.length > 0, "intermediate touch viewport must render session navigator targets");
  assert.ok(targets.every((height) => height >= 44), `intermediate session navigator targets below 44px: ${JSON.stringify(targets)}`);
  pass("intermediate touch layout", `768px viewport, ${targets.length} session navigator targets at least 44px high`);
}

async function assertReadableRevisionRows(page) {
  const separatedMetadata = await page.locator(".item-row > span").evaluateAll((items) => items.every((item) => {
    const title = item.querySelector("strong");
    const metadata = item.querySelector("small");
    if (!title || !metadata) return true;
    return metadata.getBoundingClientRect().top >= title.getBoundingClientRect().bottom;
  }));
  assert.ok(separatedMetadata, "revision titles and score metadata must be on separate readable lines");
}

async function assertToastAvoidsMobileNavigation(page) {
  const unobscured = await page.evaluate(() => {
    const toast = document.querySelector("#toast-region .toast");
    const navigation = document.querySelector("#mobile-navigation");
    if (!toast || !navigation) return true;
    return toast.getBoundingClientRect().bottom <= navigation.getBoundingClientRect().top;
  });
  assert.ok(unobscured, "a mobile status toast must not overlap the fixed navigation");
}

async function runFlows(page, screenshotDirectory, downloadDirectory) {
  await go(page, "dashboard", "Dashboard");
  assert.match(page.url(), /#\/dashboard$/);
  assert.match(await page.title(), /Dashboard.*Operating Systems Study/);
  assert.match(await page.locator("main").innerText(), /source-backed Operating Systems study workspace/i);
  assert.match(await metricText(page, "Modules"), /7/);
  assert.match(await metricText(page, "Lessons"), /21/);
  assert.match(await metricText(page, "Sources"), /21/);
  assert.match(await metricText(page, "Teaching pages"), /454/);
  assert.match(await metricText(page, "Questions"), /210/);
  assert.doesNotMatch(await page.locator("body").innerText(), /vite error|webpack|application error|runtime error overlay/i);
  assert.equal(await page.locator("#app-loading").count(), 0, "Dashboard retained a stale loading state");
  assert.equal(await page.locator('.sidebar-nav [data-route="dashboard"]').getAttribute("aria-current"), "page", "desktop primary navigation must expose the active page");
  assert.equal(await page.locator('#mobile-navigation [data-route="dashboard"]').getAttribute("aria-current"), "page", "mobile primary navigation must expose the active page");
  await capture(page, screenshotDirectory, "dashboard-desktop-light.png");
  pass("dashboard", "7 modules, 21 lessons, 21 sources, 454 teaching pages, and 210 questions");

  await go(page, "material", "Material");
  const materialSearch = page.locator('form[data-filter-form="material"] input[name="search"]');
  const firstLessonTitle = (await page.locator(".lesson-card h2").first().textContent()).trim();
  await materialSearch.fill(firstLessonTitle.slice(0, 12));
  await materialSearch.press("Tab");
  assert.match(await page.locator(".filter-result").innerText(), /[1-9]\d* of 21 lessons shown/);
  const materialModule = page.locator('form[data-filter-form="material"] select[name="moduleId"]');
  const chosenModule = await materialModule.locator("option").nth(1).getAttribute("value");
  await materialModule.selectOption(chosenModule);
  assert.match(await page.locator(".filter-result").innerText(), /lessons shown/);
  await page.locator('[data-action="reset-filters"][data-kind="material"]').click();
  await page.locator(".lesson-card").first().waitFor({ state: "visible" });
  await capture(page, screenshotDirectory, "material-desktop-light.png");
  await page.locator(".lesson-card").first().getByRole("link", { name: "Open lesson" }).click();
  await page.waitForURL(/#\/lesson\//);
  await waitForView(page, await page.getByRole("heading", { level: 1 }).textContent());
  assert.ok(await page.locator("article.material-section").count() >= 3, "selected lesson is not a long source-backed lesson");
  const lessonText = await page.locator("main").innerText();
  assert.match(lessonText, /Source material/);
  assert.match(lessonText, /Generated study guidance/);
  assert.match(lessonText, /Common mistakes/);
  assert.match(lessonText, /Misconception:.*Correction:/s);
  assert.match(lessonText, /p\. \d+/);
  assert.ok(await page.locator('article.material-section[lang="ar"][dir="rtl"]').count() >= 1, "lesson lacks generated Arabic RTL guidance");
  await page.getByRole("button", { name: "Mark completed" }).click();
  await page.getByText("Completed", { exact: true }).first().waitFor({ state: "visible" });
  await page.getByRole("button", { name: "Bookmark lesson" }).click();
  await page.getByRole("button", { name: "Remove bookmark" }).waitFor({ state: "visible" });
  await capture(page, screenshotDirectory, "lesson-desktop-light.png", { fullPage: true });
  const linkedQuestion = page.locator('article.material-section a[href^="#/questions/"]').first();
  const linkedQuestionId = (await linkedQuestion.getAttribute("href"))?.split("/").pop();
  assert.match(linkedQuestionId || "", /^gq-os-ch\d\d-part\d-\d{3}$/);
  await linkedQuestion.click();
  await waitForView(page, "Question Bank");
  assert.match(page.url(), new RegExp(`#\\/questions\\/${linkedQuestionId}$`));
  assert.equal(await page.locator("article.question-card").count(), 1, "lesson deep link must render exactly one Question Bank record");
  assert.equal(await page.locator("article.question-card").getAttribute("data-question-id"), linkedQuestionId, "lesson deep link must preserve its canonical question ID");
  pass("material and lesson", "search/filter, long lesson, source and Arabic guidance, citations, completion, and bookmark state");

  await go(page, "practice", "Practice");
  assert.match(await page.locator(".setup-summary").innerText(), /Eligible:\s*210/);
  await setSetupValue(page, "practice", "type", "mcq");
  await setSetupValue(page, "practice", "count", 6);
  await page.getByRole("button", { name: "Start Practice" }).click();
  await waitForView(page, "Practice");
  assert.equal(await page.locator(".feedback").count(), 0, "Practice leaks feedback before an answer");
  assert.equal(await page.locator(".guidance-panel").count(), 0, "Practice leaks Arabic guidance before an answer");
  assert.equal(await page.locator('form[data-answer="practice"] input[type="radio"]').count(), 4, "MCQ practice lacks four typed controls");
  const firstFeedback = await answerPractice(page, 0);
  assert.match(firstFeedback, /Correct|Wrong/);
  assert.ok(await page.locator('.guidance-panel[lang="ar"][dir="rtl"] p').count() >= 4, "Practice feedback must include a translation, 2–3 Arabic paragraphs, and note");
  await page.getByRole("button", { name: "Bookmark" }).click();
  await page.getByText("Bookmark updated.").last().waitFor({ state: "visible" });
  assert.ok(await page.locator("#toast-region .toast").count() <= 1, "rapid visible actions must retain only the latest non-blocking status toast");
  await capture(page, screenshotDirectory, "practice-feedback-desktop.png", { fullPage: true });
  await go(page, "dashboard", "Dashboard");
  await go(page, "practice", "Practice");
  assert.equal(await page.locator('form[data-answer="practice"] input:disabled').count(), 4, "revisited Practice answer is not locked");
  assert.match(await page.locator(".feedback").innerText(), /Correct|Wrong/);
  const outcomes = [firstFeedback];
  for (let index = 1; index < 6; index += 1) {
    await page.getByRole("button", { name: "Next" }).click();
    outcomes.push(await answerPractice(page, index));
  }
  assert.ok(outcomes.some((outcome) => /Wrong/.test(outcome || "")), "current generated MCQ payload unexpectedly produced no wrong response in six independent visible selections");
  await page.getByRole("button", { name: "Finish" }).click();
  await waitForView(page, "Practice complete");

  await page.getByRole("link", { name: "Try another Practice" }).click();
  await waitForView(page, "Practice");
  await setSetupValue(page, "practice", "type", "true-false");
  await setSetupValue(page, "practice", "count", 1);
  await page.getByRole("button", { name: "Start Practice" }).click();
  await waitForView(page, "Practice");
  assert.equal(await page.locator('form[data-answer="practice"] input[type="radio"]').count(), 2, "True/False session lacks two typed controls");
  await page.locator('form[data-answer="practice"] input[value="true"]').check({ force: true });
  await page.getByRole("button", { name: "Check answer" }).click();
  assert.match(await page.locator(".feedback").innerText(), /Correct|Wrong/);
  await page.getByRole("button", { name: "Finish" }).click();
  await waitForView(page, "Practice complete");
  pass("practice", "MCQ no-leak/feedback/Arabic guidance/lock/finish plus typed True/False feedback");

  await go(page, "questions", "Question Bank");
  assert.match(await page.locator(".filter-result").innerText(), /210 results\s*·\s*page 1 of 21/i);
  assert.equal(await page.locator("[data-more-menu] summary").getAttribute("aria-current"), "page", "More must expose its active state for Question Bank");
  assert.equal(await page.locator('#mobile-navigation [data-route="questions"]').getAttribute("aria-current"), "page", "the active More destination must expose its current page state");
  const firstQuestion = page.locator(".question-card").first();
  assert.ok(await firstQuestion.count(), `Question Bank produced no cards: ${await page.locator("main").innerText()}`);
  const questionId = await firstQuestion.getAttribute("data-question-id");
  assert.match(questionId || "", /^gq-os-ch\d\d-part\d-\d{3}$/);
  await firstQuestion.locator('[data-action="reveal-answer"]').click();
  await firstQuestion.getByText("Answer:", { exact: false }).waitFor({ state: "visible" });
  const guidanceLink = firstQuestion.getByRole("link", { name: "Read Arabic guidance" });
  assert.ok(await guidanceLink.count(), "revealed Question Bank answer lacks the Arabic guidance link");
  const bookmarkButton = firstQuestion.getByRole("button", { name: "Bookmark" });
  if (await bookmarkButton.count()) await bookmarkButton.click();
  await guidanceLink.click();
  await waitForView(page, "Question Explanations");
  assert.match(page.url(), new RegExp(`#\\/explanations\\/${questionId}$`));
  assert.match(await page.locator(".filter-result").innerText(), /1 bilingual explanation record/i);
  const explanationCard = page.locator("article.explanation-card").first();
  assert.equal(await page.locator("article.explanation-card").count(), 1, "record deep link must render exactly one explanation");
  assert.equal(await explanationCard.getAttribute("data-question-id"), questionId, "Arabic guidance must resolve the exact Question Bank record");
  assert.ok(await explanationCard.locator('[lang="en"][dir="ltr"]').count(), "Arabic guidance destination lacks the linked English source prompt");
  assert.ok(await explanationCard.locator('[lang="ar"][dir="rtl"] p').count() >= 4, "Arabic guidance destination lacks the translation, paragraphs, or note");
  assert.ok(await explanationCard.locator(".citation").count(), "Arabic guidance destination lacks citations");
  pass("question bank and explanations", "paginated Question Bank, revealed and followed a canonical Arabic-guidance deep link without search, then verified exactly one full guidance record and citations");
  await page.goto(applicationUrl("questions/gq-os-ch99-part9-999"), { waitUntil: "networkidle" });
  await waitForView(page, "Page not found");
  assert.match(await page.locator("main").innerText(), /unavailable/i);

  await go(page, "exam", "Mock Exam");
  assert.equal(await page.locator("[data-more-menu] summary").getAttribute("aria-current"), null, "More must clear its active state outside More destinations");
  await setSetupValue(page, "exam", "count", 2);
  await setSetupValue(page, "exam", "minutes", 1);
  await page.getByRole("button", { name: "Start Mock Exam" }).click();
  await waitForView(page, "Mock Exam");
  assert.equal(await page.locator(".feedback, .guidance-panel").count(), 0, "active exam leaks feedback or guidance fields");
  const activeExamText = await page.locator("main").innerText();
  assert.doesNotMatch(activeExamText, /Rationale:|الترجمة والشرح|إرشاد دراسي مولد/);
  await page.locator('form[data-answer="exam"] .answer-row').first().click();
  await page.getByRole("button", { name: "Save answer" }).click();
  await page.getByRole("button", { name: "Flag question" }).click();
  await page.getByRole("button", { name: "Bookmark" }).click();
  await page.getByRole("button", { name: "Next" }).click();
  await capture(page, screenshotDirectory, "exam-active-desktop.png");
  await page.getByRole("button", { name: "Submit" }).click();
  await page.getByRole("dialog").waitFor({ state: "visible" });
  await page.getByRole("dialog").getByRole("button", { name: "Submit exam" }).click();
  await waitForView(page, "Mock Exam results");
  const resultText = await page.locator("main").innerText();
  assert.match(resultText, /Scoreable.*Correct.*Incorrect.*Unanswered.*Percentage.*Duration/s);
  assert.match(resultText, /Rationale:/);
  assert.ok(await page.locator('.guidance-panel[lang="ar"][dir="rtl"]').count() >= 1, "finalized exam does not reveal Arabic review guidance");
  pass("mock exam", "answer-only active surface, answer/save/flag/bookmark/navigation/submit, then totals and Arabic review");

  await go(page, "revision", "Revision");
  assert.match(await page.locator("main").innerText(), /Answered/);
  await go(page, "mistakes", "Mistakes");
  assert.ok(await page.locator(".item-row").count() >= 1, "wrong Practice activity did not appear in Mistakes");
  await page.getByRole("button", { name: "Practice" }).first().click();
  await waitForView(page, "Practice");
  await page.getByRole("button", { name: "Finish" }).click();
  await waitForView(page, "Practice complete");
  await go(page, "bookmarks", "Bookmarks");
  assert.match(await page.locator("main").innerText(), /Questions/);
  assert.ok(await page.locator(".item-row").count() >= 2, "lesson and question bookmarks are not both visible");
  const questionSection = page.locator("section.panel").filter({ has: page.getByRole("heading", { name: "Questions" }) });
  await questionSection.getByRole("button", { name: "Practice" }).first().click();
  await waitForView(page, "Practice");
  await page.getByRole("button", { name: "Finish" }).click();
  await waitForView(page, "Practice complete");
  await go(page, "revision", "Revision");
  await go(page, "settings", "Settings");
  await page.getByRole("button", { name: "Use dark theme" }).click();
  assert.equal(await page.locator("html").getAttribute("data-theme"), "dark");
  await go(page, "revision", "Revision");
  await capture(page, screenshotDirectory, "revision-desktop-dark.png");
  await assertReadableRevisionRows(page);
  pass("revision, mistakes, and bookmarks", "prior sessions, ranked mistake Practice, separate bookmarks, focused action, and dark revision view");

  await page.setViewportSize({ width: 768, height: 900 });
  await go(page, "settings", "Settings");
  await page.getByRole("radio", { name: "Light" }).focus();
  const themeFocus = await page.getByRole("radio", { name: "Light" }).evaluate((input) => getComputedStyle(input.closest("label")).outlineStyle);
  assert.equal(themeFocus, "solid", "theme radio focus must visibly outline its label");
  await page.goto(applicationUrl("practice"), { waitUntil: "networkidle" });
  if (await page.getByRole("heading", { level: 1, name: "Practice complete" }).count()) {
    await page.getByRole("link", { name: "Try another Practice" }).click();
  }
  await waitForView(page, "Practice");
  await setSetupValue(page, "practice", "count", 1);
  await page.getByRole("button", { name: "Start Practice" }).click();
  await waitForView(page, "Practice");
  await assertIntermediateTouchTargets(page);
  await page.getByRole("button", { name: "Finish" }).click();
  await waitForView(page, "Practice complete");
  await page.setViewportSize({ width: 1440, height: 1000 });

  await go(page, "settings", "Settings");
  const downloadPromise = page.waitForEvent("download");
  await page.getByRole("button", { name: "Export progress JSON" }).click();
  const download = await downloadPromise;
  const exportFile = join(downloadDirectory, "os-study-progress.json");
  await download.saveAs(exportFile);
  const exported = JSON.parse(await readFile(exportFile, "utf8"));
  assert.equal(exported.projectId, "operating-systems-study", "exported progress uses the wrong project key");
  const exportedSummary = exportedProgressSummary(exported);
  assert.ok(exportedSummary.answered > 0, "exported progress must include scored activity before persistence checks");
  await page.reload({ waitUntil: "networkidle" });
  await waitForView(page, "Settings");
  assert.equal(await page.locator("html").getAttribute("data-theme"), "dark", "theme did not persist after reload");
  await go(page, "revision", "Revision");
  await assertRevisionProgress(page, exportedSummary);
  await go(page, "settings", "Settings");
  await page.getByRole("button", { name: "Reset progress" }).click();
  const resetDialog = page.getByRole("dialog");
  await resetDialog.waitFor({ state: "visible" });
  assert.equal(await page.evaluate(() => document.activeElement?.textContent?.trim()), "Reset progress");
  await page.keyboard.press("Tab");
  assert.equal(await page.evaluate(() => document.activeElement?.textContent?.trim()), "Cancel");
  await page.keyboard.press("Shift+Tab");
  assert.equal(await page.evaluate(() => document.activeElement?.textContent?.trim()), "Reset progress");
  await resetDialog.getByRole("button", { name: "Cancel" }).click();
  await go(page, "revision", "Revision");
  await assertRevisionProgress(page, exportedSummary);
  await go(page, "settings", "Settings");
  await page.getByRole("button", { name: "Reset progress" }).click();
  await resetDialog.getByRole("button", { name: "Reset progress" }).click();
  await page.getByText("OS Study progress was reset.").waitFor({ state: "visible" });
  await go(page, "revision", "Revision");
  await assertRevisionProgress(page, {
    projectId: "operating-systems-study",
    completedLessons: 0,
    answered: 0,
    correct: 0,
    incorrect: 0,
  });
  await go(page, "settings", "Settings");
  await page.locator("#progress-import").setInputFiles(exportFile);
  await page.getByText("Progress imported successfully.").waitFor({ state: "visible" });
  await go(page, "revision", "Revision");
  await assertRevisionProgress(page, exportedSummary);
  await go(page, "settings", "Settings");
  const restoredDownloadPromise = page.waitForEvent("download");
  await page.getByRole("button", { name: "Export progress JSON" }).click();
  const restoredDownload = await restoredDownloadPromise;
  const restoredExportFile = join(downloadDirectory, "os-study-progress-restored.json");
  await restoredDownload.saveAs(restoredExportFile);
  assert.deepEqual(JSON.parse(await readFile(restoredExportFile, "utf8")), exported);
  pass("settings", `exported, reloaded, reset, and restored exact progress at ${exportFile}; dark theme and Cancel focus trap also persisted`);

  await page.setViewportSize({ width: 390, height: 844 });
  await go(page, "settings", "Settings");
  await page.getByRole("button", { name: "Use light theme" }).click();
  await assertToastAvoidsMobileNavigation(page);
  await go(page, "dashboard", "Dashboard");
  await capture(page, screenshotDirectory, "dashboard-mobile-light.png");
  await go(page, "practice", "Practice");
  await setSetupValue(page, "practice", "type", "mcq");
  await setSetupValue(page, "practice", "count", 1);
  await page.getByRole("button", { name: "Start Practice" }).click();
  await waitForView(page, "Practice");
  await answerPractice(page, 0);
  await capture(page, screenshotDirectory, "practice-mobile-feedback.png", { fullPage: true });
  await assertMobileLayout(page);
}

async function main() {
  const screenshotDirectory = await createScreenshotDirectory();
  const downloadDirectory = await mkdtemp(join(tmpdir(), "os-study-download-"));
  let server = null;
  let browser = null;
  try {
    server = await ensureServer();
    browser = await launchBrowser();
    const context = await browser.newContext({ viewport: { width: 1440, height: 1000 }, acceptDownloads: true });
    await context.clearCookies();
    const page = await context.newPage();
    attachEventCollection(page);
    await page.goto(applicationUrl("dashboard"), { waitUntil: "networkidle" });
    await page.evaluate(() => { localStorage.clear(); sessionStorage.clear(); });
    await page.reload({ waitUntil: "networkidle" });
    pass("site state", "cleared LocalStorage and sessionStorage in the fresh temporary browser context");
    await runFlows(page, screenshotDirectory, downloadDirectory);
    assertBrowserHealth(browserEvents);
    const warnings = browserEvents.console.filter((event) => event.type === "warning");
    pass("browser health", `page errors 0; console errors 0; console warnings ${warnings.length}; failed requests 0; essential data failures 0`);
    console.log(`PASS screenshots: ${screenshotDirectory}`);
    for (const screenshot of screenshots) console.log(`SCREENSHOT ${screenshot.name} ${screenshot.width}x${screenshot.height} ${screenshot.file}`);
  } finally {
    if (browser) await browser.close();
    await stopServer(server);
  }
}

main().catch((error) => {
  console.error(`FAIL browser QA: ${error.stack || error.message}`);
  process.exitCode = 1;
});
