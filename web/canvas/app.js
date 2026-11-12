import { App } from "@modelcontextprotocol/ext-apps";

// The official SDK checks the parent message source and negotiates ui/initialize.
// Test execution is reachable only through the shared reviewed-plan controls.
const app = new App(
  { name: "RepoGraph Canvas", version: "1.0.0" },
  {},
  { strict: true },
);
let argumentsForView = {};
let connected = false;
let busy = false;
const status = (text) => {
  document.getElementById("bridge-status").textContent = text;
};
function show(result) {
  if (result.isError)
    throw new Error(
      "The analysis request failed. Inspect the agent's tool result.",
    );
  let report = result.structuredContent;
  if (!report) {
    const content = result.content?.find((item) => item.type === "text");
    if (content) report = JSON.parse(content.text);
  }
  if (
    !report ||
    report.schema_version !== 1 ||
    !Array.isArray(report.nodes) ||
    report.nodes.length > 200 ||
    !Array.isArray(report.edges) ||
    report.edges.length > 800
  ) {
    throw new Error("The host returned an unsupported canvas report.");
  }
  window.RepoGraphCanvas.mount(report);
  if (report.scenario?.kind === "proposed_content") {
    argumentsForView = { ...argumentsForView };
    // A preview can only be refreshed from the original host inputs, not a virtual snapshot ID.
    status("Proposed content · Source unchanged");
  } else {
    argumentsForView = report.request || argumentsForView;
    status("Connected to repository");
  }
  document.getElementById("bridge-actions").hidden = false;
}
app.ontoolinput = ({ arguments: args }) => {
  argumentsForView = args || {};
};
app.ontoolresult = (result) => {
  try {
    show(result);
  } catch (error) {
    status(error.message);
  }
};
app.ontoolcancelled = () =>
  status("Analysis cancelled. The previous view is retained.");
app.onteardown = async () => {
  window.RepoGraphCanvas.dispose();
  return {};
};
window.RepoGraphCanvas.request = async (changes) => {
  if (!connected) throw new Error("The canvas is not connected to a host.");
  if (busy) return;
  busy = true;
  document.getElementById("nodes").inert = true;
  document.getElementById("inspector-content").inert = true;
  document.getElementById("refresh").disabled = true;
  status("Reading source evidence…");
  try {
    const result = await app.callServerTool({
      name: "get_repository_canvas",
      arguments: { ...argumentsForView, ...changes },
    });
    show(result);
  } catch (error) {
    status("Could not update this view. Check the agent's MCP connection.");
    throw error;
  } finally {
    busy = false;
    document.getElementById("nodes").inert = false;
    document.getElementById("inspector-content").inert = false;
    document.getElementById("refresh").disabled = false;
  }
};
const allowed = new Set([
  "get_repository_readiness",
  "index_repository",
  "discover_tests",
  "prepare_verification",
  "verify_changes",
  "get_verification_result",
]);
window.RepoGraphCanvas.call = async (name, args) => {
  if (!connected || !allowed.has(name))
    throw new Error("This canvas action is unavailable.");
  const result = await app.callServerTool({ name, arguments: args });
  if (result.isError)
    throw new Error(
      result.content?.find((item) => item.type === "text")?.text ||
        "The repository request failed.",
    );
  return (
    result.structuredContent ||
    JSON.parse(result.content.find((item) => item.type === "text").text)
  );
};
app
  .connect()
  .then(() => {
    connected = true;
    status("Connected · Waiting for analysis");
    window.RepoGraphCanvas.workbench.connect(window.RepoGraphCanvas.call);
  })
  .catch(() =>
    status(
      "MCP Apps connection unavailable. Ask the agent for an offline HTML export.",
    ),
  );
