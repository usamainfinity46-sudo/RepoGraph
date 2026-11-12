import {
  AppBridge,
  PostMessageTransport,
} from "@modelcontextprotocol/ext-apps/app-bridge";
const iframe = document.createElement("iframe");
iframe.setAttribute("sandbox", "allow-scripts");
iframe.style.cssText = "width:100%;height:1100px;border:0";
document.body.append(iframe);
const bridge = new AppBridge(
  null,
  { name: "RepoGraph protocol test host", version: "1.0.0" },
  { serverTools: {}, serverResources: {} },
  { hostContext: { theme: "light" } },
);
window.calls = [];
bridge.oncalltool = async (params) => {
  window.calls.push(params);
  if (window.refuseNext) {
    window.refuseNext = false;
    return { isError: true, content: [{ type: "text", text: "Test refusal" }] };
  }
  return (
    await fetch("/call", { method: "POST", body: JSON.stringify(params) })
  ).json();
};
bridge.oninitialized = async () => {
  await bridge.sendToolInput({ arguments: { mode: "repository", limit: 6 } });
  const result = await (await fetch("/initial")).json();
  await bridge.sendToolResult(result);
  window.appInitialized = true;
};
window.bridge = bridge;
await bridge.connect(
  new PostMessageTransport(iframe.contentWindow, iframe.contentWindow),
);
iframe.src = "/app";
