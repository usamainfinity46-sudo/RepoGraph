import { createServer } from "node:http";
import { readFile } from "node:fs/promises";
import { resolve } from "node:path";
import { spawn } from "node:child_process";
import { build } from "esbuild";
import { Client } from "@modelcontextprotocol/client";
import { StdioClientTransport } from "@modelcontextprotocol/client/stdio";
const root = resolve(import.meta.dirname, "../../..");
const fixture = resolve(root, ".repograph/canvas-qa");
const transport = new StdioClientTransport({
  command: process.env.REPOGRAPH_PYTHON,
  args: [
    "-m",
    "repograph",
    "--root",
    resolve(fixture, "checkout-example"),
    "--enable-verification",
    "--python-executable",
    process.env.REPOGRAPH_PYTHON,
    "serve",
  ],
  cwd: root,
  stderr: "pipe",
});
const client = new Client(
  { name: "Canvas browser engineering test", version: "1.0.0" },
  {
    capabilities: {
      extensions: {
        "io.modelcontextprotocol/ui": {
          mimeTypes: ["text/html;profile=mcp-app"],
        },
      },
    },
  },
);
await client.connect(transport);
const localArgs = process.env.REPOGRAPH_KIT_BIN
  ? [
      process.env.REPOGRAPH_KIT_BIN,
      "canvas",
      "--root",
      resolve(fixture, "node-example-host"),
      "--cache-dir",
      resolve(fixture, "runtime-cache"),
      "--enable-verification",
      "--no-open",
      "--json",
    ]
  : [
      "-m",
      "repograph",
      "--root",
      resolve(fixture, "node-example-host"),
      "--enable-verification",
      "--node-executable",
      process.execPath,
      "--no-open",
      "--launch-json",
      "canvas-live",
    ];
const local = spawn(
  process.env.REPOGRAPH_KIT_BIN
    ? process.execPath
    : process.env.REPOGRAPH_PYTHON,
  localArgs,
  { cwd: root, stdio: ["ignore", "pipe", "pipe"], windowsHide: true },
);
let localStartup;
await new Promise((resolveReady, reject) => {
  let buffer = "";
  local.stdout.on("data", (chunk) => {
    buffer += chunk;
    for (;;) {
      const end = buffer.indexOf("\n");
      if (end < 0) break;
      const line = buffer.slice(0, end);
      buffer = buffer.slice(end + 1);
      try {
        const value = JSON.parse(line);
        if (value.url) {
          localStartup = value;
          resolveReady();
        }
      } catch {}
    }
  });
  local.once("error", reject);
  local.once("exit", (code) =>
    reject(new Error(`Local canvas exited (${code}) before startup`)),
  );
});
const hostJS = (
  await build({
    entryPoints: [resolve(import.meta.dirname, "host-client.js")],
    bundle: true,
    write: false,
    format: "esm",
    platform: "browser",
    target: "es2022",
  })
).outputFiles[0].contents;
const server = createServer(async (req, res) => {
  try {
    if (req.url === "/health") {
      res.end("ready");
      return;
    }
    if (req.url === "/local-info") {
      res.setHeader("Content-Type", "application/json");
      res.end(JSON.stringify(localStartup));
      return;
    }
    if (req.url === "/host") {
      res.setHeader("Content-Type", "text/html");
      res.end(
        '<!doctype html><html lang="en"><title>MCP Apps engineering host</title><body style="margin:0"><script type="module" src="/host.js"></script></body></html>',
      );
      return;
    }
    if (req.url === "/host.js") {
      res.setHeader("Content-Type", "text/javascript");
      res.end(hostJS);
      return;
    }
    if (req.url === "/app") {
      const result = await client.readResource({
        uri: "ui://repograph/canvas.html",
      });
      res.setHeader("Content-Type", "text/html");
      res.end(result.contents[0].text);
      return;
    }
    if (req.url === "/initial") {
      res.setHeader("Content-Type", "application/json");
      res.end(
        JSON.stringify(
          await client.callTool({
            name: "open_repository_canvas",
            arguments: { mode: "repository", limit: 6 },
          }),
        ),
      );
      return;
    }
    if (req.url === "/call" && req.method === "POST") {
      let body = "";
      for await (const chunk of req) {
        body += chunk;
        if (body.length > 2_500_000) throw new Error("oversized");
      }
      const params = JSON.parse(body);
      if (
        ![
          "get_repository_canvas",
          "get_repository_readiness",
          "index_repository",
          "discover_tests",
          "prepare_verification",
          "verify_changes",
          "get_verification_result",
        ].includes(params.name)
      )
        throw new Error("Tool not allowed");
      res.setHeader("Content-Type", "application/json");
      res.end(JSON.stringify(await client.callTool(params)));
      return;
    }
    if (
      /^\/(repository|impact|empty|partial|scenario|proposed|cited|hostile|large)\.html$/.test(
        req.url,
      )
    ) {
      res.setHeader("Content-Type", "text/html");
      res.end(await readFile(resolve(fixture, req.url.slice(1))));
      return;
    }
    res.statusCode = 404;
    res.end("Not found");
  } catch (error) {
    res.statusCode = 500;
    res.end(JSON.stringify({ error: String(error) }));
  }
});
server.listen(43187, "127.0.0.1");
for (const signal of ["SIGTERM", "SIGINT"])
  process.on(signal, async () => {
    server.close();
    local.kill("SIGTERM");
    await client.close();
    process.exit(0);
  });
