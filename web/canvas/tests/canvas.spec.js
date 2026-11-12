import { test, expect } from "@playwright/test";
import AxeBuilder from "@axe-core/playwright";
import { readFile, writeFile } from "node:fs/promises";
import { resolve } from "node:path";
const url = (name) => `http://127.0.0.1:43187/${name}.html`;

test("live repository launch, reviewed tests, saved results, changes and failed verification", async ({
  page,
  request,
}) => {
  const response = await request.get("http://127.0.0.1:43187/local-info");
  const info = await response.json();
  const executed = [];
  page.on("request", (r) => {
    if (
      r.url().endsWith("/api/call") &&
      r.postDataJSON()?.name === "verify_changes"
    )
      executed.push(r.postDataJSON());
  });
  await page.goto(info.url);
  await expect(page.locator("#repo-name")).toHaveText("node-example-host");
  await expect(page.locator("#workbench")).toBeVisible();
  await expect(page.locator("#workbench-status")).toContainText("approval");
  await page.locator("#discover-tests").click();
  await expect(page.locator(".test-choice")).toHaveCount(1);
  await expect(page.locator("#test-framework")).toHaveValue("node:test");
  const accessibility = await new AxeBuilder({ page })
    .withTags(["wcag2a", "wcag2aa", "wcag21aa"])
    .analyze();
  expect(accessibility.violations).toEqual([]);
  await page.locator(".test-choice input").check();
  await page.locator("#review-tests").click();
  await expect(page.locator("#test-plan")).toBeVisible();
  await expect(page.locator("#plan-command")).toContainText("--test");
  await expect(page.locator("#plan-command")).toContainText("checkout.test.js");
  expect(executed).toHaveLength(0);
  await page.locator("#decline-plan").click();
  expect(executed).toHaveLength(0);
  await page.locator("#review-tests").click();
  await page.locator("#approve-plan").click();
  await expect(page.locator("#live-test-result")).toContainText(
    "Verification passed",
    { timeout: 20000 },
  );
  await expect(page.locator("#live-test-result")).toContainText("1 passed");
  expect(executed).toHaveLength(1);
  await expect(page.locator("#workbench-status")).toContainText(
    "Results are saved",
  );
  await page.screenshot({
    path: "../../.repograph/canvas-qa/live-tests-passed.png",
    fullPage: true,
  });
  await page.reload();
  await expect(page.locator("#verification")).toContainText(
    "Saved verification",
  );
  const pricing = resolve(
    import.meta.dirname,
    "../../../.repograph/canvas-qa/node-example-host/pricing.js",
  );
  const original = await readFile(pricing, "utf8");
  try {
    await writeFile(
      pricing,
      "export function discount(price) { return price * 0.8; }\n",
    );
    await page.locator("#working-changes").click();
    await expect(page.locator("#changes")).toBeVisible();
    await expect(page.locator("#changes")).toContainText("pricing.js");
    await page.locator("#discover-tests").click();
    await expect(page.locator(".test-choice")).toHaveCount(1);
    await page.locator("#test-scope").selectOption("targeted");
    await page.locator(".test-choice input").check();
    await page.locator("#review-tests").click();
    await expect(page.locator("#test-plan")).toBeVisible();
    await page.locator("#approve-plan").click();
    await expect(page.locator("#live-test-result")).toContainText(
      "Verification failed",
      { timeout: 20000 },
    );
    await expect(page.locator("#live-test-result")).toContainText("1 failed");
    expect(executed).toHaveLength(2);
    await page.screenshot({
      path: "../../.repograph/canvas-qa/live-change-failed-test.png",
      fullPage: true,
    });
  } finally {
    await writeFile(pricing, original);
  }
});

test("live API denies missing authorization and cross-site requests", async ({
  request,
}) => {
  const info = await (
    await request.get("http://127.0.0.1:43187/local-info")
  ).json();
  const parsed = new URL(info.url);
  const missing = await request.post(parsed.origin + "/api/call", {
    headers: { Origin: parsed.origin },
    data: { name: "get_repository_canvas", arguments: {} },
  });
  expect(missing.status()).toBe(401);
  const cross = await request.post(parsed.origin + "/api/call", {
    headers: { Origin: "https://attacker.invalid" },
    data: {
      name: "verify_changes",
      arguments: { plan_id: "x", approved: true },
    },
  });
  expect(cross.status()).toBe(403);
});

test("repository map, selection, search, zoom, tour and source evidence", async ({
  page,
}) => {
  const errors = [];
  page.on("pageerror", (e) => errors.push(e.message));
  await page.goto(url("repository"));
  await expect(page.locator("#repo-name")).toHaveText("checkout-example");
  await page.screenshot({
    path: "../../.repograph/canvas-qa/initial-desktop.png",
    fullPage: true,
  });
  await expect(page.locator(".node")).toHaveCount(7);
  await page.locator("#detailed").click();
  await expect(page.locator(".node")).toHaveCount(14);
  await page
    .getByRole("button", { name: "function total, checkout.py:2" })
    .click();
  await expect(page.locator("#inspector-content")).toContainText(
    "checkout.py:2",
  );
  await expect(page.locator("#inspector-content")).toContainText(
    "calls discount",
  );
  const zoom = await page.locator("#zoom-label").innerText();
  await page.locator("#zoom-in").click();
  await expect(page.locator("#zoom-label")).not.toHaveText(zoom);
  const viewport = page.locator("#viewport");
  const box = await viewport.boundingBox();
  const before = await page.locator("#scene").getAttribute("style");
  await page.mouse.move(box.x + 7, box.y + 7);
  await page.mouse.down();
  await page.mouse.move(box.x + 45, box.y + 25);
  await page.mouse.up();
  await expect(page.locator("#scene")).not.toHaveAttribute("style", before);
  await viewport.focus();
  const dragged = await page.locator("#scene").getAttribute("style");
  await page.keyboard.press("ArrowRight");
  await expect(page.locator("#scene")).not.toHaveAttribute("style", dragged);
  await page.locator("#search").fill("receipt");
  await expect(page.locator(".node")).toHaveCount(4);
  await page.locator("#search").fill("not-found");
  await expect(page.locator("#empty")).toBeVisible();
  await page.locator("#search").fill("");
  await page.locator("#tour").click();
  await expect(page.locator("#tour-title")).toContainText("1 / 3");
  await page.locator("#help").click();
  await expect(page.locator("#limitations")).toBeVisible();
  await page.keyboard.press("Escape");
  await expect(page.locator("#limitations")).not.toBeVisible();
  expect(errors).toEqual([]);
  await page.screenshot({
    path: "../../.repograph/canvas-qa/repository-desktop.png",
    fullPage: true,
  });
});

test("large repositories collapse into readable folder groups with source drilldown", async ({
  page,
}) => {
  await page.goto(url("large"));
  await expect(page.locator(".folder-node")).toHaveCount(4);
  await expect(page.locator("#scope")).toContainText(
    "arrows aggregate cross-folder imports",
  );
  await page
    .getByRole("button", { name: "Folder core, 6 included modules" })
    .click();
  await expect(page.locator(".folder-node")).toHaveCount(0);
  await expect(page.locator(".node")).toHaveCount(6);
  await page.getByRole("button", { name: "Show all folders" }).click();
  await expect(page.locator(".folder-node")).toHaveCount(4);
  await page.screenshot({
    path: "../../.repograph/canvas-qa/folder-groups.png",
    fullPage: true,
  });
});

test("impact trace, test suggestions and interpreted explanations remain distinct", async ({
  page,
}) => {
  await page.goto(url("cited"));
  await page.screenshot({
    path: "../../.repograph/canvas-qa/impact-desktop.png",
    fullPage: true,
  });
  await page
    .getByRole("button", { name: "function receipt, receipt.py:2" })
    .click();
  await expect(page.locator("#inspector-content")).toContainText(
    "2 semantic hops",
  );
  await page.locator("#walk").click();
  await expect(page.locator("#walk-title")).toHaveText("Relationship 1 of 2");
  await page.locator("#walk").click();
  await expect(page.locator("#walk-copy")).toContainText("not execution order");
  await page
    .getByRole("button", { name: "function total, checkout.py:2" })
    .click();
  await expect(page.locator("#inspector-content")).toContainText(
    "Agent interpretation",
  );
  await page.locator('[data-view="tests"]').first().click();
  await expect(page.locator(".test-card")).toHaveCount(2);
  await page.locator(".test-card").first().click();
  await expect(page.locator("#inspector-content")).toContainText(
    "Not executed",
  );
});

test("scenario and content preview clearly preserve hypothetical status", async ({
  page,
}) => {
  await page.goto(url("scenario"));
  await expect(page.locator("#scenario")).toContainText("Source unchanged");
  await expect(page.locator("#scenario")).toContainText("Assumption:");
  await page.goto(url("proposed"));
  await expect(page.locator("#scenario")).toContainText("removed nodes");
  await page
    .getByRole("button", { name: "function discount, pricing.py:1" })
    .click();
  await expect(page.locator("#inspector-content")).toContainText("pricing.py");
});

test("hostile repository text stays inert and no external requests occur", async ({
  page,
}) => {
  const external = [];
  page.on("request", (r) => {
    if (!r.url().startsWith("http://127.0.0.1:43187/")) external.push(r.url());
  });
  await page.goto(url("hostile"));
  await expect(page.locator("#repo-name")).toContainText("</script>");
  expect(await page.evaluate(() => window.compromised)).toBeUndefined();
  expect(await page.locator("img").count()).toBe(0);
  expect(external).toEqual([]);
});

test("empty and partial views are explicit", async ({ page }) => {
  await page.goto(url("empty"));
  await expect(page.locator("#empty")).toContainText("No nodes");
  await page.goto(url("partial"));
  await expect(page.locator("#notices")).toContainText("Partial canvas");
});

test("mobile and reduced-motion view remain usable", async ({ page }) => {
  await page.setViewportSize({ width: 390, height: 844 });
  await page.emulateMedia({ reducedMotion: "reduce" });
  await page.goto(url("impact"));
  await expect(page.locator(".mobile-nav")).toBeVisible();
  await page.locator('.mobile-nav [data-view="tests"]').click();
  await expect(page.locator(".test-card")).toHaveCount(2);
  expect(
    await page.evaluate(
      () => document.documentElement.scrollWidth <= window.innerWidth,
    ),
  ).toBe(true);
  await page.screenshot({
    path: "../../.repograph/canvas-qa/mobile.png",
    fullPage: true,
  });
});

test("keyboard access and accessibility contrast pass", async ({ page }) => {
  await page.goto(url("repository"));
  const results = await new AxeBuilder({ page })
    .withTags(["wcag2a", "wcag2aa", "wcag21aa"])
    .analyze();
  expect(
    results.violations.map((v) => ({
      id: v.id,
      nodes: v.nodes.map((n) => n.target),
    })),
  ).toEqual([]);
  await page.locator("#detailed").focus();
  await page.keyboard.press("Enter");
  await expect(page.locator("#detailed")).toHaveAttribute(
    "aria-pressed",
    "true",
  );
});

test("official MCP Apps handshake, real stdio roundtrip, paging, scenarios and errors", async ({
  page,
}) => {
  const errors = [];
  page.on("pageerror", (e) => errors.push(e.message));
  await page.goto("http://127.0.0.1:43187/host");
  const app = page.frameLocator("iframe");
  await expect(app.locator("#repo-name")).toHaveText("checkout-example");
  await expect(app.locator("#bridge-status")).toContainText("Connected");
  await app.locator("body").evaluate(() =>
    window.postMessage(
      {
        jsonrpc: "2.0",
        method: "ui/notifications/tool-result",
        params: { structuredContent: { repository_name: "Spoofed parent" } },
      },
      "*",
    ),
  );
  await expect(app.locator("#repo-name")).toHaveText("checkout-example");
  await app.locator("#next-page").click();
  await expect
    .poll(() =>
      page.evaluate(
        () =>
          window.calls.filter((c) => c.name === "get_repository_canvas").length,
      ),
    )
    .toBe(1);
  await expect(app.locator("#scope")).toContainText("6 of 14");
  await app.locator("#refresh").click();
  await expect
    .poll(() =>
      page.evaluate(
        () =>
          window.calls.filter((c) => c.name === "get_repository_canvas").length,
      ),
    )
    .toBe(2);
  await expect(app.locator("#bridge-status")).toHaveText(
    "Connected to repository",
  );
  await app.locator(".node").first().click();
  await app.getByRole("button", { name: "What if I change this?" }).click();
  await expect(app.locator("#scenario")).toContainText("Source unchanged");
  await page.evaluate(() => {
    window.refuseNext = true;
  });
  await app.locator("#refresh").click();
  await expect(app.locator("#bridge-status")).toContainText("Could not update");
  await expect(app.locator("#scenario")).toBeVisible();
  await expect
    .poll(() =>
      page.evaluate(
        () =>
          window.calls.filter((c) => c.name === "get_repository_canvas").length,
      ),
    )
    .toBe(4);
  const methods = await page.evaluate(() => window.calls.map((c) => c.name));
  expect(new Set(methods)).toEqual(
    new Set(["get_repository_canvas", "get_repository_readiness"]),
  );
  await page.evaluate(() => window.bridge.teardownResource({}));
  expect(errors).toEqual([]);
});

test("MCP Apps also reviews and executes the approved test plan", async ({
  page,
}) => {
  await page.goto("http://127.0.0.1:43187/host");
  const app = page.frameLocator("iframe");
  await expect(app.locator("#repo-name")).toHaveText("checkout-example");
  await app.locator("#discover-tests").click();
  await expect(app.locator(".test-choice")).toHaveCount(2);
  await app.locator(".test-choice input").first().check();
  await app.locator("#review-tests").click();
  await expect(app.locator("#plan-command")).toContainText("pytest");
  await expect(app.locator("#plan-command")).toContainText("test_checkout.py");
  expect(
    await page.evaluate(
      () => window.calls.filter((c) => c.name === "verify_changes").length,
    ),
  ).toBe(0);
  await app.locator("#approve-plan").click();
  await expect(app.locator("#live-test-result")).toContainText(
    "Verification passed",
    { timeout: 20000 },
  );
  expect(
    await page.evaluate(
      () => window.calls.filter((c) => c.name === "verify_changes").length,
    ),
  ).toBe(1);
});

test("the local canvas can be stopped from its own interface", async ({
  page,
  request,
}) => {
  const info = await (
    await request.get("http://127.0.0.1:43187/local-info")
  ).json();
  await page.goto(info.url);
  await expect(page.locator("#repo-name")).toHaveText("node-example-host");
  await page.locator("#stop-local").click();
  await expect(page.locator("#bridge-status")).toHaveText(
    "Canvas stopped. You can close this tab.",
  );
});
