#!/usr/bin/env node
import fs from 'node:fs';
import path from 'node:path';
import { fileURLToPath } from 'node:url';
import { parseArgs } from 'node:util';
import { createInterface } from 'node:readline/promises';
import { AGENTS, planSetup, applySetup } from '../lib/config.mjs';
import { defaultCache, loadRelease, runtimePaths, runtimeReady, ensureRuntime } from '../lib/runtime.mjs';

const packageRoot = path.dirname(path.dirname(fileURLToPath(import.meta.url)));
const metadata = JSON.parse(fs.readFileSync(path.join(packageRoot, 'package.json'), 'utf8'));

async function main() {
  const { values, positionals } = parseArgs({ allowPositionals: true, options: {
    agent: { type: 'string' }, root: { type: 'string' }, 'cache-dir': { type: 'string' },
    'dry-run': { type: 'boolean' }, json: { type: 'boolean' }, help: { type: 'boolean', short: 'h' }, version: { type: 'boolean', short: 'v' },
  } });
  if (values.version) { console.log(metadata.version); return; }
  const command = positionals[0] || 'setup';
  if (values.help) {
    console.log(`repograph-kit ${metadata.version}
Usage: repograph-kit setup [--agent codex|claude-code|cursor|copilot|all] [--root PATH]
       repograph-kit setup --agent AGENT --dry-run
       repograph-kit doctor [--root PATH]
Options: --cache-dir PATH   Isolated backend cache (default: user cache)
         --json            Print setup/doctor result as JSON
Setup installs the bundled Python server, skill and project MCP entry.
Requires Node 22+, and uv or Python 3.11-3.13. Test execution stays disabled.
npm install itself has no setup hooks. Run setup explicitly.`);
    return;
  }
  if (positionals.length > 1 || !['setup', 'doctor'].includes(command)) throw new Error('Use setup, doctor or --help');
  const root = fs.realpathSync(values.root || process.cwd());
  if (!fs.statSync(root).isDirectory()) throw new Error('Project root must be a directory');
  const release = loadRelease(packageRoot);
  const runtime = runtimePaths(values['cache-dir'] || defaultCache(), release);
  if (command === 'doctor') {
    const ready = runtimeReady(runtime, release);
    const report = { ready, root, serverVersion: release.serverVersion, python: runtime.python };
    console.log(values.json ? JSON.stringify(report) : ready ? 'RepoGraph backend is installed. Reload your configured agent and call health.' : 'Backend not installed. Run repograph-kit setup in your project.');
    if (!ready) process.exitCode = 1;
    return;
  }
  let selected = values.agent;
  if (!selected) {
    if (!process.stdin.isTTY || !process.stdout.isTTY) throw new Error('Specify --agent codex, claude-code, cursor, copilot or all in non-interactive sessions');
    const prompt = createInterface({ input: process.stdin, output: process.stdout });
    try { selected = (await prompt.question('Agent (codex / claude-code / cursor / copilot / all): ')).trim(); }
    finally { prompt.close(); }
  }
  const agents = selected === 'all' ? Object.keys(AGENTS) : [selected];
  const writes = planSetup(root, agents, runtime.python, release.skillFiles);
  const report = { dryRun: !!values['dry-run'], root, agents, serverVersion: release.serverVersion,
    backendInstallNeeded: !runtimeReady(runtime, release), files: writes.map(item => item.relative), verificationEnabled: false };
  if (!values['dry-run']) {
    ensureRuntime(runtime, release, root);
    applySetup(writes);
  }
  console.log(values.json ? JSON.stringify(report) : values['dry-run']
    ? `Would configure ${agents.join(', ')} for ${root}; ${writes.length} file changes; backend install ${report.backendInstallNeeded ? 'needed' : 'already complete'}.`
    : `RepoGraph is ready for ${agents.join(', ')}. Reload your agent, approve its MCP connection if prompted, and ask it to use RepoGraph. Test execution is disabled.`);
}

main().catch(error => { console.error(`repograph-kit: ${error.message}`); process.exitCode = 1; });
