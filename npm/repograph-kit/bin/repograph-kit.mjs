#!/usr/bin/env node
import fs from 'node:fs';
import path from 'node:path';
import { fileURLToPath } from 'node:url';
import { parseArgs } from 'node:util';
import { createInterface } from 'node:readline/promises';
import { spawn } from 'node:child_process';
import { AGENTS, planSetup, applySetup, inspectConfiguration, managedOptions } from '../lib/config.mjs';
import { defaultCache, loadRelease, runtimePaths, runtimeReady, ensureRuntime } from '../lib/runtime.mjs';
import { configurationReport, projectReadiness, readinessText } from '../lib/doctor.mjs';

const packageRoot = path.dirname(path.dirname(fileURLToPath(import.meta.url)));
const metadata = JSON.parse(fs.readFileSync(path.join(packageRoot, 'package.json'), 'utf8'));

async function main() {
  const { values, positionals } = parseArgs({ allowPositionals: true, options: {
    agent: { type: 'string' }, root: { type: 'string' }, 'cache-dir': { type: 'string' },
    'dry-run': { type: 'boolean' }, json: { type: 'boolean' }, help: { type: 'boolean', short: 'h' }, version: { type: 'boolean', short: 'v' },
    upgrade: { type: 'boolean' }, 'enable-verification': { type: 'boolean' }, 'disable-verification': { type: 'boolean' },
    'python-executable': { type: 'string' }, 'node-executable': { type: 'string' }, 'jest-entry': { type: 'string' }, 'vitest-entry': { type: 'string' },
    port: {type:'string'}, 'no-open': {type:'boolean'},
    'pytest-plugin':{type:'string',multiple:true},
  } });
  if (values.version) { console.log(metadata.version); return; }
  const command = positionals[0] || 'setup';
  if (values.help) {
    console.log(`repograph-kit ${metadata.version}
Usage: repograph-kit setup [--agent codex|claude-code|cursor|copilot|all] [--root PATH]
       repograph-kit setup --agent AGENT --dry-run
       repograph-kit doctor [--root PATH]
       repograph-kit canvas [--root PATH] [--enable-verification] [--no-open]
Options: --cache-dir PATH   Isolated backend cache (default: user cache)
         --json            Print setup/doctor result or canvas launch as JSON
         --upgrade         Update recognized stock configuration and skill files
         --enable-verification  Opt in to approved test execution (off by default)
         --disable-verification Remove execution opt-in during an upgrade
         --python-executable PATH  Project Python interpreter with pytest installed
         --node-executable PATH    Host Node executable for Jest/Vitest
         --jest-entry PATH / --vitest-entry PATH  Installed runner entry
         --pytest-plugin MODULE    Explicitly approved installed pytest plugin
         --port NUMBER     Local canvas port (default: automatically selected)
         --no-open         Print the canvas URL without opening a browser
Setup installs the bundled Python server, skill and project MCP entry.
Requires Node 22+, and uv or Python 3.11-3.13. No tests run during setup/doctor.
npm install itself has no setup hooks. Run setup explicitly.`);
    return;
  }
  if (positionals.length > 1 || !['setup', 'doctor', 'canvas'].includes(command)) throw new Error('Use setup, doctor, canvas or --help');
  const root = fs.realpathSync(values.root || process.cwd());
  if (!fs.statSync(root).isDirectory()) throw new Error('Project root must be a directory');
  const release = loadRelease(packageRoot);
  const runtime = runtimePaths(values['cache-dir'] || defaultCache(), release);
  if (values['enable-verification'] && values['disable-verification']) throw new Error('Choose either --enable-verification or --disable-verification');
  if (command === 'canvas') {
    if (values.port && (!/^\d+$/.test(values.port) || Number(values.port)>65535)) throw new Error('Port must be 0..65535');
    // A checked-in client entry cannot grant execution to a standalone browser session.
    const flags=[];
    if(values['enable-verification'])flags.push('--enable-verification');
    for(const flag of ['python-executable','node-executable','jest-entry','vitest-entry'])if(values[flag]){
      const index=flags.indexOf('--'+flag);if(index>=0)flags.splice(index,2);
      flags.push('--'+flag,path.resolve(values[flag]));
    }
    if(!flags.includes('--node-executable'))flags.push('--node-executable',process.execPath);
    for(const plugin of values['pytest-plugin']||[])flags.push('--pytest-plugin',plugin);
    if(flags.includes('--enable-verification')&&!flags.includes('--python-executable')){
      const projectPython=path.join(root,'.venv',process.platform==='win32'?'Scripts/python.exe':'bin/python');
      if(fs.existsSync(projectPython))flags.push('--python-executable',projectPython);
    }
    const launch=['-I','-m','repograph','--root',root,...flags,'--port',values.port||'0'];
    if(values['no-open'])launch.push('--no-open');
    if(values.json)launch.push('--launch-json');
    launch.push('canvas-live');
    if(values['dry-run']){console.log(JSON.stringify({dryRun:true,root,python:runtime.python,args:launch}));return;}
    ensureRuntime(runtime,release,root);
    const child=spawn(runtime.python,launch,{shell:false,stdio:'inherit',windowsHide:true,
      env:Object.fromEntries(Object.entries(process.env).filter(([key])=>!/^(PYTHON|VIRTUAL_ENV$)/i.test(key)))});
    child.on('error',error=>{console.error(`repograph-kit: ${error.message}`);process.exitCode=1;});
    child.on('exit',code=>{process.exitCode=code??1;});
    process.on('SIGINT',()=>child.kill('SIGINT'));
    process.on('SIGTERM',()=>child.kill('SIGTERM'));
    return;
  }
  if (command === 'doctor') {
    if (values.agent && !Object.hasOwn(AGENTS, values.agent) && values.agent !== 'all') throw new Error('Unknown agent');
    const backendReady = runtimeReady(runtime, release);
    const configuration = configurationReport(root, runtime.python);
    const selected = values.agent && values.agent !== 'all' ? [values.agent] : Object.keys(AGENTS);
    const configured = selected.filter(agent => configuration[agent].currentBackend);
    const entries = inspectConfiguration(root);
    const flags = configured.length ? managedOptions(entries[configured[0]].entry, root, [runtime.python]) : [];
    const project = backendReady ? projectReadiness(runtime, root, flags) : null;
    const ready = backendReady && configured.length > 0 && project.ready_for_indexing;
    const report = { ready, backendReady, root, serverVersion: release.serverVersion, python: runtime.python, configuration, project, guiConnectionVerified: false };
    console.log(values.json ? JSON.stringify(report) : [
      backendReady ? 'RepoGraph backend is installed.' : 'Backend not installed. Run repograph-kit setup in your project.',
      `Current agent entries: ${configured.join(', ') || 'none; run setup or upgrade the existing entry'}.`,
      ...(project ? [readinessText(project)] : []),
      'Client connection is not verified by doctor. Reload the agent, review its workspace/MCP prompt, and call health.',
    ].join('\n'));
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
  const previous = JSON.parse(fs.readFileSync(new URL('../lib/previous-releases.json', import.meta.url), 'utf8'));
  const cache = values['cache-dir'] || defaultCache();
  const options = { upgrade: !!values.upgrade, previousPythons: previous.map(item => runtimePaths(cache, item).python), previousSkillHashes: previous.map(item => item.skillFiles) };
  if (values['enable-verification'] || values['disable-verification']) options.verificationEnabled = !!values['enable-verification'];
  for (const flag of ['python-executable', 'node-executable', 'jest-entry', 'vitest-entry']) {
    if (values[flag]) options['--' + flag] = path.resolve(values[flag]);
  }
  const writes = planSetup(root, agents, runtime.python, release.skillFiles, options);
  const report = { dryRun: !!values['dry-run'], root, agents, serverVersion: release.serverVersion,
    backendInstallNeeded: !runtimeReady(runtime, release), files: writes.map(item => item.relative), verificationEnabled: options.verificationEnabled || false };
  if (!values['dry-run']) {
    ensureRuntime(runtime, release, root);
    applySetup(writes);
    report.configuration = configurationReport(root, runtime.python);
    report.verificationEnabled = agents.every(agent => report.configuration[agent].verificationEnabled);
    const entry = inspectConfiguration(root)[agents[0]].entry;
    report.project = projectReadiness(runtime, root, managedOptions(entry, root, [runtime.python]));
    report.guiConnectionVerified = false;
  }
  console.log(values.json ? JSON.stringify(report) : values['dry-run']
    ? `Would configure ${agents.join(', ')} for ${root}; ${writes.length} file changes; backend install ${report.backendInstallNeeded ? 'needed' : 'already complete'}.`
    : `RepoGraph configuration written for ${agents.join(', ')}.\n${readinessText(report.project)}\nReload your agent, review its workspace/MCP connection prompt, then ask it to call health and index_repository.`);
}

main().catch(error => { console.error(`repograph-kit: ${error.message}`); process.exitCode = 1; });
