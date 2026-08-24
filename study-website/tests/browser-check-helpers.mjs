import assert from "node:assert/strict";

function eventText(events) {
  return events.map((event) => event.text).join(" | ");
}

export function assertBrowserHealth(events) {
  const consoleErrors = events.console.filter((event) => event.type === "error");
  const consoleWarnings = events.console.filter((event) => event.type === "warning");

  assert.deepEqual(events.pageErrors, [], `page errors: ${events.pageErrors.join(" | ")}`);
  assert.deepEqual(consoleErrors, [], `console errors: ${eventText(consoleErrors)}`);
  assert.deepEqual(consoleWarnings, [], `console warnings: ${eventText(consoleWarnings)}`);
  assert.deepEqual(events.failedRequests, [], `failed requests: ${events.failedRequests.join(" | ")}`);
  assert.deepEqual(
    events.essentialDataFailures,
    [],
    `non-2xx data requests: ${events.essentialDataFailures.join(" | ")}`,
  );
}

export async function terminateStartedChild(child) {
  if (!child || child.exitCode !== null) return;
  await new Promise((resolve, reject) => {
    const cleanup = () => {
      child.removeListener("exit", onExit);
      child.removeListener("error", onError);
    };
    const onExit = () => {
      cleanup();
      resolve();
    };
    const onError = (error) => {
      cleanup();
      reject(error);
    };
    child.once("exit", onExit);
    child.once("error", onError);
    try {
      const signalled = child.kill();
      if (!signalled && child.exitCode !== null) onExit();
    } catch (error) {
      onError(error);
    }
  });
}

export async function waitForReadinessWithCleanup(child, waitForReadiness) {
  try {
    return await waitForReadiness();
  } catch (error) {
    await terminateStartedChild(child);
    throw error;
  }
}
