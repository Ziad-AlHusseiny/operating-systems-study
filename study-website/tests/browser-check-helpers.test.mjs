import assert from "node:assert/strict";
import { EventEmitter } from "node:events";
import test from "node:test";

import {
  assertBrowserHealth,
  waitForReadinessWithCleanup,
} from "./browser-check-helpers.mjs";

class TestChild extends EventEmitter {
  constructor() {
    super();
    this.exitCode = null;
    this.killCalls = 0;
  }

  kill() {
    this.killCalls += 1;
    queueMicrotask(() => {
      this.exitCode = 1;
      this.emit("exit", 1);
    });
    return true;
  }
}

test("browser health rejects every console warning", () => {
  assert.throws(
    () => assertBrowserHealth({
      pageErrors: [],
      console: [{ type: "warning", text: "unexpected warning" }],
      failedRequests: [],
      essentialDataFailures: [],
    }),
    /console warnings: unexpected warning/,
  );
});

test("readiness failure terminates and waits for the exact started child", async () => {
  const child = new TestChild();

  await assert.rejects(
    waitForReadinessWithCleanup(child, async () => {
      throw new Error("readiness failed");
    }),
    /readiness failed/,
  );

  assert.equal(child.killCalls, 1);
  assert.equal(child.exitCode, 1);
});
