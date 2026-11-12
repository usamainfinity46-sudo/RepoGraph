/* Same-origin local transport. The bearer is never sent in a query or Referer. */
(() => {
  "use strict";
  const canvas = window.RepoGraphCanvas,
    $ = (id) => document.getElementById(id);
  const supplied = new URLSearchParams(location.hash.slice(1)).get("token");
  let stored = null;
  try {
    stored = sessionStorage.getItem("repograph-canvas-token");
    if (supplied) {
      if (stored !== supplied)
        sessionStorage.removeItem("repograph-canvas-view");
      sessionStorage.setItem("repograph-canvas-token", supplied);
      history.replaceState(null, "", location.pathname);
    }
  } catch {
    /* The launch fragment still works if browser storage is disabled. */
  }
  const token = supplied || stored;
  let argumentsForView = { mode: "repository", limit: 200 },
    busy = false;
  try {
    const saved = JSON.parse(
      sessionStorage.getItem("repograph-canvas-view") || "null",
    );
    if (saved && typeof saved === "object" && !Array.isArray(saved))
      argumentsForView = saved;
  } catch {}
  async function call(name, args) {
    const response = await fetch("/api/call", {
      method: "POST",
      headers: {
        "Content-Type": "application/json",
        Authorization: "Bearer " + token,
      },
      body: JSON.stringify({ name, arguments: args }),
    });
    const body = await response.json();
    if (!response.ok)
      throw new Error(
        `${body.error?.code || "request_failed"}: ${body.error?.message || "Canvas request failed"}`,
      );
    return body;
  }
  canvas.request = async (changes) => {
    if (busy) return;
    busy = true;
    $("bridge-status").textContent = "Reading repository evidence…";
    try {
      const report = await call("get_repository_canvas", {
        ...argumentsForView,
        ...changes,
      });
      argumentsForView = report.request;
      try {
        sessionStorage.setItem(
          "repograph-canvas-view",
          JSON.stringify(argumentsForView),
        );
      } catch {}
      canvas.mount(report);
      $("bridge-actions").hidden = false;
      $("bridge-status").textContent = "Live local connection · No uploads";
      document
        .querySelectorAll(".saved-tag")
        .forEach((n) => (n.textContent = "Live canvas"));
    } catch (error) {
      $("bridge-status").textContent = error.message;
      throw error;
    } finally {
      busy = false;
    }
  };
  canvas.call = call;
  $("stop-local").hidden = false;
  $("stop-local").onclick = async (event) => {
    if (!event.isTrusted) return;
    try {
      await call("stop_canvas", {});
      try {
        sessionStorage.removeItem("repograph-canvas-token");
        sessionStorage.removeItem("repograph-canvas-view");
      } catch {}
      $("bridge-status").textContent =
        "Canvas stopped. You can close this tab.";
      document
        .querySelectorAll("button")
        .forEach((button) => (button.disabled = true));
    } catch (error) {
      $("bridge-status").textContent = error.message;
    }
  };
  canvas.workbench
    .connect(call)
    .then(() => canvas.request({}))
    .catch((error) => {
      $("bridge-status").textContent = error.message;
    });
})();
