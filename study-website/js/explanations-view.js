export function limitExplanationEntries(entries, visibleCount = 15) {
  return entries.slice(0, Math.max(0, visibleCount));
}

export function increaseVisibleCount(current, total, step = 15) {
  return Math.min(current + step, total);
}
