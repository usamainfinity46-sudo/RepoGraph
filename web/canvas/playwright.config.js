import { defineConfig } from "@playwright/test";
import { resolve } from "node:path";
const repo = resolve(import.meta.dirname, "../..");
export default defineConfig({
  testDir: "./tests",
  timeout: 30000,
  fullyParallel: false,
  workers: 1,
  reporter: [
    ["list"],
    ["json", { outputFile: "../../.repograph/canvas-qa/browser-results.json" }],
  ],
  outputDir: "../../.repograph/canvas-qa/test-results",
  use: {
    viewport: { width: 1440, height: 1050 },
    trace: "retain-on-failure",
    launchOptions: process.env.REPOGRAPH_BROWSER
      ? { executablePath: process.env.REPOGRAPH_BROWSER }
      : {},
  },
  webServer: {
    command: "node tests/host.mjs",
    url: "http://127.0.0.1:43187/health",
    reuseExistingServer: false,
    timeout: 30000,
    env: {
      REPOGRAPH_PYTHON:
        process.env.REPOGRAPH_PYTHON ||
        resolve(
          repo,
          process.platform === "win32"
            ? ".venv/Scripts/python.exe"
            : ".venv/bin/python",
        ),
    },
  },
  projects: [{ name: "chromium", use: { browserName: "chromium" } }],
});
