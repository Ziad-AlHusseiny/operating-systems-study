export function limitExplanationEntries(entries, visibleCount = 15) {
  return entries.slice(0, Math.max(0, visibleCount));
}

export function increaseVisibleCount(current, total, step = 15) {
  return Math.min(current + step, total);
}

export function renderMobileMoreMenu() {
  return `<details class="mobile-more">
    <summary class="mobile-nav__item">More</summary>
    <div class="mobile-more__menu">
      <a class="mobile-more__link" href="#/revision" data-route="revision">Revision Summary</a>
      <a class="mobile-more__link" href="#/explanations" data-route="explanations">Question Explanations</a>
    </div>
  </details>`;
}

export function explanationFocusSelector({ filterName, questionId } = {}) {
  if (["search", "source", "topic", "type"].includes(filterName)) {
    return `[data-explanation-filter-form] [name="${filterName}"]`;
  }
  if (/^q-\d{3}$/.test(questionId || "")) {
    return `[data-action="bookmark"][data-id="${questionId}"]`;
  }
  return null;
}
