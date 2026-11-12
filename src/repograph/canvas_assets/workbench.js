/* Shared controls for the authenticated local browser and MCP Apps transports. */
(() => {
  "use strict";
  const canvas = window.RepoGraphCanvas,
    $ = (id) => document.getElementById(id);
  const node = (tag, text, cls) => {
    const n = document.createElement(tag);
    if (text !== undefined) n.textContent = text;
    if (cls) n.className = cls;
    return n;
  };
  let rpc = null,
    report = null,
    readiness = null,
    files = [],
    nextOffset = null,
    plan = null,
    running = false,
    active = false;
  const checked = new Set();
  const message = (text) => {
    $("workbench-status").textContent = text;
  };
  const failure = (error) => {
    message(error.message || "The repository request failed.");
  };
  async function action(work) {
    if (running || active) return;
    active = true;
    document
      .querySelectorAll("#workbench button")
      .forEach((b) => (b.disabled = true));
    try {
      await work();
    } catch (error) {
      failure(error);
    } finally {
      active = false;
      document
        .querySelectorAll("#workbench button")
        .forEach((b) => (b.disabled = false));
    }
  }
  function testChoices() {
    const framework = $("test-framework").value,
      scope = $("test-scope").value;
    $("test-file-choices").replaceChildren();
    const matching = files.filter((f) => f.frameworks.includes(framework));
    for (const file of matching) {
      const label = node("label", undefined, "test-choice");
      const input = node("input");
      input.type = "checkbox";
      input.checked = checked.has(file.path);
      input.disabled = scope === "suite" || running;
      input.onchange = () => {
        if (input.checked) checked.add(file.path);
        else checked.delete(file.path);
        testChoices();
      };
      label.append(
        input,
        node("span", file.path),
        node("small", `${file.total_definitions} static test definitions`),
      );
      $("test-file-choices").append(label);
    }
    const selected = matching.filter((f) => checked.has(f.path)).length;
    $("test-selection-status").textContent =
      `${files.length} discovered files in this preview · ${matching.length} for ${framework} · ${selected} selected${nextOffset !== null ? " · More files available" : ""}`;
    $("review-tests").disabled =
      running ||
      !readiness ||
      (scope === "targeted" && (selected === 0 || selected > 50));
    $("more-tests").hidden = nextOffset === null;
    if (selected > 50)
      $("test-selection-status").textContent +=
        " · Select at most 50 files or choose the broader suite.";
  }
  async function discover(offset = 0) {
    $("testing-panel").hidden = false;
    message("Discovering tests without executing them…");
    const result = await rpc("discover_tests", { offset, limit: 200 });
    files = offset ? [...files, ...result.files] : result.files;
    nextOffset = result.next_offset ?? null;
    for (const test of report?.tests?.tests || []) checked.add(test.path);
    if (report?.tests?.broader_run_recommended) $("test-scope").value = "suite";
    testChoices();
    message(
      result.complete
        ? "Test discovery complete. No tests have run."
        : "Test discovery is incomplete. Review diagnostics before selecting a scope.",
    );
  }
  async function refresh(mode) {
    const before = report?.snapshot_ids[0];
    message("Refreshing the source index. No repository code executes…");
    const indexed = await rpc("index_repository", {});
    if (!indexed.published)
      throw new Error(
        indexed.scan.diagnostics
          .map((d) => (d.path ? d.path + ": " : "") + d.message)
          .join(" ") ||
          "Index could not be published. Check source limits and ignore rules.",
      );
    await canvas.request({
      mode,
      paths: null,
      node_ids: null,
      query: "",
      offset: 0,
      snapshot_id: indexed.snapshot_id,
      before_snapshot_id: mode === "changes" ? before : null,
      intent: "",
      assumptions: [],
      proposed_files: [],
    });
    message(
      mode === "changes"
        ? "Current changes and potential dependents are ready."
        : "Repository index refreshed.",
    );
  }
  $("show-repository").onclick = () =>
    action(async () => {
      await canvas.request({
        mode: "repository",
        paths: null,
        node_ids: null,
        query: "",
        offset: 0,
        snapshot_id: null,
        before_snapshot_id: null,
        intent: "",
        assumptions: [],
        proposed_files: [],
      });
      message(
        "Repository map ready. Use folder groups and paging to explore every module.",
      );
    });
  $("search-repository").onclick = () =>
    action(async () => {
      await canvas.request({
        mode: "repository",
        query: $("repository-search").value,
        paths: null,
        node_ids: null,
        offset: 0,
        before_snapshot_id: null,
        intent: "",
        assumptions: [],
        proposed_files: [],
      });
      message(
        "Search results use the full indexed repository, not just the current page.",
      );
    });
  $("repository-search").onkeydown = (event) => {
    if (event.key === "Enter") $("search-repository").click();
  };
  $("refresh-index").onclick = () => action(() => refresh("repository"));
  $("working-changes").onclick = () => action(() => refresh("changes"));
  $("discover-tests").onclick = () => action(() => discover());
  $("close-testing").onclick = () => {
    $("testing-panel").hidden = true;
  };
  $("more-tests").onclick = () => action(() => discover(nextOffset));
  $("test-framework").onchange = () => {
    checked.clear();
    testChoices();
  };
  $("test-scope").onchange = testChoices;
  $("review-tests").onclick = () =>
    action(async () => {
      const framework = $("test-framework").value,
        scope = $("test-scope").value;
      const paths =
        scope === "suite"
          ? null
          : files
              .filter(
                (f) => f.frameworks.includes(framework) && checked.has(f.path),
              )
              .map((f) => f.path);
      message("Preparing a reviewable plan. Tests have not started…");
      plan = await rpc("prepare_verification", { framework, scope, paths });
      $("plan-scope").textContent =
        `${plan.framework} · ${plan.scope} · ${plan.paths.length} pinned files · ${plan.timeout_seconds}s timeout · Expires ${new Date(plan.expires_at * 1000).toLocaleTimeString()}`;
      $("plan-cwd").textContent = `Working directory: ${plan.cwd}`;
      $("plan-command").textContent = JSON.stringify(plan.command, null, 2);
      $("plan-warnings").replaceChildren(
        ...plan.warnings.map((text) => node("p", text)),
      );
      if (!plan.execution_enabled)
        $("plan-warnings").append(
          node(
            "p",
            "Execution is disabled by the host. Relaunch with --enable-verification to review and approve test runs.",
          ),
        );
      $("approve-plan").disabled = !plan.execution_enabled;
      $("test-plan").showModal();
      message("Review the exact command and scope before approving.");
    });
  function cancel() {
    plan = null;
    $("approve-plan").disabled = true;
    $("test-plan").close();
    message("Plan cancelled. No tests ran.");
  }
  $("cancel-plan").onclick = cancel;
  $("decline-plan").onclick = cancel;
  $("test-plan").oncancel = () => {
    plan = null;
    $("approve-plan").disabled = true;
  };
  function displayResult(result) {
    const cases = node("div"),
      caption = node("p"),
      more = node("button", "More case results", "action-button");
    let shown = 0,
      next = result.next_offset ?? null;
    function append(items) {
      for (const item of items) {
        cases.append(node("p", `${item.status} · ${item.path} · ${item.name}`));
        if (item.message && ["failed", "error"].includes(item.status))
          cases.append(node("pre", item.message));
      }
      shown += items.length;
      caption.textContent = `Showing ${shown} of ${result.total_cases} saved cases. This run does not establish coverage outside its reviewed scope.`;
      more.hidden = next === null;
    }
    $("live-test-result").replaceChildren(
      node("h3", `Verification ${result.status}`),
      node(
        "p",
        `${result.counts.passed} passed · ${result.counts.failed} failed · ${result.counts.errors} errors · ${result.counts.skipped} skipped`,
      ),
      node("p", `Saved plan ${result.plan_id}`),
    );
    for (const diagnostic of result.diagnostics)
      $("live-test-result").append(node("p", diagnostic.message));
    $("live-test-result").append(
      caption,
      cases,
      more,
      node("pre", result.output),
    );
    append(result.cases);
    more.onclick = () =>
      action(async () => {
        const page = await rpc("get_verification_result", {
          plan_id: result.plan_id,
          offset: next,
          limit: 200,
        });
        next = page.next_offset ?? null;
        append(page.cases);
      });
  }
  $("approve-plan").onclick = async (event) => {
    if (!event.isTrusted || !plan || !plan.execution_enabled || running) return;
    const approvedPlan = plan;
    plan = null;
    running = true;
    $("stop-local").disabled = true;
    $("approve-plan").disabled = true;
    $("test-plan").close();
    testChoices();
    message("Running the approved test plan…");
    try {
      const result = await rpc("verify_changes", {
        plan_id: approvedPlan.id,
        approved: true,
      });
      displayResult(result);
      await canvas.request({ verification_plan_id: result.plan_id });
      message(
        `Verification ${result.status}. Results are saved; nothing will run again automatically.`,
      );
    } catch (error) {
      failure(error);
    } finally {
      running = false;
      $("stop-local").disabled = false;
      testChoices();
    }
  };
  document.addEventListener("repograph:mounted", (event) => {
    report = event.detail;
    if (report.verification) displayResult(report.verification);
  });
  canvas.workbench = {
    async connect(call) {
      rpc = call;
      $("workbench").hidden = false;
      try {
        readiness = await rpc("get_repository_readiness", {});
        const framework = readiness.test_frameworks.find((f) =>
          ["pytest", "jest", "vitest", "node:test"].includes(f),
        );
        if (framework) $("test-framework").value = framework;
        $("testing-policy").textContent = readiness.verification_enabled
          ? "Execution is enabled for this session. Every run needs a reviewed plan and your approval."
          : "Execution is off. Test discovery and recommendations work; relaunch with --enable-verification to approve runs.";
        message(
          `${readiness.source_files} source files · ${readiness.tests_found} test files · ${readiness.verification_enabled ? "Review and approval required for execution" : "Analysis only; execution disabled"}`,
        );
      } catch (error) {
        failure(error);
      }
    },
  };
})();
