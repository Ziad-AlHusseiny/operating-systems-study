import test from "node:test";
import assert from "node:assert/strict";
import {
  explanationFocusSelector,
  increaseVisibleCount,
  limitExplanationEntries,
  renderMobileMoreMenu,
} from "../js/explanations-view.js";

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
