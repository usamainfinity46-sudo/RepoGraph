import fs from 'node:fs';
import path from 'node:path';
import crypto from 'node:crypto';
import { isDeepStrictEqual } from 'node:util';
import { parseTree, getNodeValue, modify, applyEdits } from 'jsonc-parser';
import { parse as parseToml } from 'smol-toml';

export const AGENTS = {
  codex: { skill: '.agents/skills/repograph', config: '.codex/config.toml' },
  'claude-code': { skill: '.claude/skills/repograph', config: '.mcp.json', key: 'mcpServers' },
  cursor: { skill: '.cursor/skills/repograph', config: '.cursor/mcp.json', key: 'mcpServers' },
  copilot: { skill: '.github/skills/repograph', config: '.vscode/mcp.json', key: 'servers' },
};

function object(value) {
  return value !== null && typeof value === 'object' && !Array.isArray(value);
}

function sameEntry(value, entry) {
  // Parsers intentionally return null-prototype records; compare their data.
  return object(value) && isDeepStrictEqual({ ...value }, entry);
}

function jsonConfig(text) {
  const errors = [];
  const tree = parseTree(text || '{}', errors, { allowTrailingComma: true });
  if (errors.length || tree?.type !== 'object') throw new Error('MCP config must be a JSON/JSONC object');
  function unique(node) {
    if (node.type === 'object') {
      const keys = new Set();
      for (const property of node.children || []) {
        const key = property.children[0].value;
        if (keys.has(key)) throw new Error('MCP config has duplicate keys; resolve them first');
        keys.add(key);
      }
    }
    for (const child of node.children || []) unique(child);
  }
  unique(tree);
  return getNodeValue(tree);
}

export function mergeJson(text, key, entry) {
  const data = jsonConfig(text);
  if (Object.hasOwn(data, key) && !object(data[key])) throw new Error(`MCP ${key} must be an object`);
  const servers = Object.hasOwn(data, key) ? data[key] : {};
  if (Object.hasOwn(servers, 'repograph')) {
    if (sameEntry(servers.repograph, entry)) return text;
    throw new Error('A different repograph MCP entry already exists; review it before replacing it');
  }
  const result = applyEdits(text || '{}', modify(text || '{}', [key, 'repograph'], entry, {
    formattingOptions: { insertSpaces: true, tabSize: 2, eol: text.includes('\r\n') ? '\r\n' : '\n' },
  }));
  jsonConfig(result);
  return result;
}

export function mergeToml(text, entry) {
  let data;
  try { data = parseToml(text); } catch { throw new Error('Codex config is invalid TOML; resolve it first'); }
  if (Object.hasOwn(data, 'mcp_servers') && !object(data.mcp_servers)) throw new Error('mcp_servers must be a table');
  if (data.mcp_servers && Object.hasOwn(data.mcp_servers, 'repograph')) {
    if (sameEntry(data.mcp_servers.repograph, entry)) return text;
    throw new Error('A different repograph MCP entry already exists; review it before replacing it');
  }
  const block = '\n[mcp_servers.repograph]\n'
    + `command = ${JSON.stringify(entry.command)}\n`
    + `args = ${JSON.stringify(entry.args)}\n`;
  const result = text + (text.endsWith('\n') || !text ? '' : '\n') + block;
  try { parseToml(result); } catch {
    throw new Error('Cannot extend this Codex TOML layout without rewriting it; add the MCP entry manually');
  }
  return result;
}

export function projectPath(root, relative) {
  if (!relative || path.isAbsolute(relative) || relative.split(/[\\/]/).some(p => p === '..' || !p)) {
    throw new Error('Setup path must stay inside the selected project');
  }
  const target = path.resolve(root, relative);
  let current = root;
  for (const part of relative.split(/[\\/]/)) {
    current = path.join(current, part);
    try {
      const stat = fs.lstatSync(current);
      if (stat.isSymbolicLink()) throw new Error('Setup refuses symlink/junction destinations');
      if (current !== target && !stat.isDirectory()) throw new Error('Setup parent is not a directory');
      if (current === target && !stat.isFile()) throw new Error('Setup destination is not a regular file');
    } catch (error) { if (error.code !== 'ENOENT') throw error; }
  }
  return target;
}

function readOptional(target) {
  try {
    if (fs.statSync(target).size > 1_048_576) throw new Error('Setup file exceeds the 1 MiB limit');
    return fs.readFileSync(target);
  } catch (error) { if (error.code === 'ENOENT') return null; throw error; }
}

export function planSetup(root, agents, python, skillFiles) {
  const writes = [];
  const entry = { command: python, args: ['-I', '-m', 'repograph', '--root', root, 'serve'] };
  for (const agent of agents) {
    const spec = AGENTS[agent];
    if (!spec) throw new Error(`Unsupported agent: ${agent}`);
    const config = projectPath(root, spec.config);
    const before = readOptional(config);
    const text = before?.toString('utf8') || '';
    const merged = agent === 'codex' ? mergeToml(text, entry) : mergeJson(text, spec.key, { type: 'stdio', ...entry });
    writes.push({ root, relative: spec.config, target: config, before, after: Buffer.from(merged) });
    for (const [name, bytes] of Object.entries(skillFiles)) {
      const relative = `${spec.skill}/${name}`;
      const target = projectPath(root, relative);
      const original = readOptional(target);
      if (original && original.toString('utf8').replaceAll('\r\n', '\n') !== bytes.toString('utf8').replaceAll('\r\n', '\n')) {
        throw new Error(`Existing skill file differs: ${relative}. Preserve or move your changes first.`);
      }
      writes.push({ root, relative, target, before: original, after: original || bytes });
    }
  }
  return writes.filter(item => item.before === null || !item.before.equals(item.after));
}

function atomicWrite(target, bytes) {
  const temporary = `${target}.repograph-kit-${crypto.randomUUID()}`;
  try {
    fs.writeFileSync(temporary, bytes, { flag: 'wx', mode: fs.existsSync(target) ? fs.statSync(target).mode & 0o777 : 0o600 });
    fs.renameSync(temporary, target);
  } finally { if (fs.existsSync(temporary)) fs.unlinkSync(temporary); }
}

export function applySetup(writes) {
  for (const item of writes) {
    projectPath(item.root, item.relative);
    const current = readOptional(item.target);
    if (!isDeepStrictEqual(current, item.before)) throw new Error('Project configuration changed during setup; retry after review');
  }
  const applied = [];
  try {
    for (const item of writes) {
      projectPath(item.root, item.relative);
      fs.mkdirSync(path.dirname(item.target), { recursive: true });
      atomicWrite(item.target, item.after);
      applied.push(item);
    }
  } catch (error) {
    for (const item of applied.reverse()) {
      if (item.before === null) fs.unlinkSync(item.target);
      else atomicWrite(item.target, item.before);
    }
    throw error;
  }
}
