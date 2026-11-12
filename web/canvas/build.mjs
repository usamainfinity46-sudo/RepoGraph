import { build } from "esbuild";
import { readFile, writeFile } from "node:fs/promises";
import { fileURLToPath } from "node:url";
import { dirname, join } from "node:path";
const result = await build({
  entryPoints: [fileURLToPath(new URL("app.js", import.meta.url))],
  bundle: true,
  write: false,
  format: "iife",
  platform: "browser",
  target: "es2022",
  minify: true,
  legalComments: "eof",
  charset: "ascii",
  metafile: true,
});
const output = new URL(
  "../../src/repograph/canvas_assets/app.bundle.js",
  import.meta.url,
);
const bytes = result.outputFiles[0].contents;
const packages = new Map();
for (const input of Object.keys(result.metafile.inputs)) {
  if (!input.includes("node_modules")) continue;
  let directory = dirname(input);
  while (directory.includes("node_modules")) {
    try {
      const pkg = JSON.parse(
        await readFile(join(directory, "package.json"), "utf8"),
      );
      if (pkg.name && !packages.has(pkg.name)) {
        const notices = [];
        for (const name of [
          "LICENSE",
          "LICENSE.txt",
          "LICENSE.md",
          "NOTICE",
          "NOTICE.txt",
        ]) {
          try {
            notices.push(await readFile(join(directory, name), "utf8"));
          } catch {}
        }
        if (!notices.length) throw new Error(`Missing license for ${pkg.name}`);
        packages.set(
          pkg.name,
          `${pkg.name} ${pkg.version} (${pkg.license || "see license"})\n${notices.join("\n")}`,
        );
      }
      break;
    } catch (error) {
      if (error.code !== "ENOENT") throw error;
      directory = dirname(directory);
    }
  }
}
const licenses =
  [...packages]
    .sort(([a], [b]) => a.localeCompare(b))
    .map(([, text]) => text)
    .join("\n\n--------------------\n\n") + "\n";
const licensesOutput = new URL(
  "../../src/repograph/canvas_assets/third_party_licenses.txt",
  import.meta.url,
);
if (process.argv.includes("--check")) {
  if (!Buffer.from(await readFile(output)).equals(Buffer.from(bytes))) {
    throw new Error(
      "Canvas app bundle differs from its locked source. Run npm run build.",
    );
  }
  console.log("Canvas app bundle matches its source.");
  if ((await readFile(licensesOutput, "utf8")) !== licenses)
    throw new Error("Canvas license notices differ from source.");
} else {
  await writeFile(output, bytes);
  await writeFile(licensesOutput, licenses);
  console.log(`Built canvas app (${bytes.length} bytes).`);
}
