import assert from 'node:assert/strict';
import fs from 'node:fs';
import os from 'node:os';
import path from 'node:path';
import { test, mock } from 'node:test';
import { parse as parseToml } from 'smol-toml';
import { parse as parseJson } from 'jsonc-parser';
import { AGENTS, mergeJson, mergeToml, planSetup, applySetup, projectPath } from '../lib/config.mjs';

function fixture(t) {
  const root = fs.realpathSync(fs.mkdtempSync(path.join(os.tmpdir(), 'repograph-kit-test-')));
  t.after(() => fs.rmSync(root, { recursive: true, force: true }));
  return root;
}

const entry = { command: '/installed backend/python', args: ['-I', '-m', 'repograph', '--root', '/project', 'serve'] };
const skill = { 'SKILL.md': Buffer.from('---\nname: repograph\ndescription: Example\n---\n'), 'references/setup.md': Buffer.from('Setup\n') };

test('JSONC merge preserves comments and unrelated server settings; repeat is unchanged', () => {
  const before = '// Keep this comment\n{ "mcpServers": { "other": { "url": "https://example.invalid" }, }, "theme": "dark", }';
  const result = mergeJson(before, 'mcpServers', entry);
  assert.ok(result.includes('// Keep this comment'));
  assert.equal(parseJson(result).theme, 'dark');
  assert.equal(parseJson(result).mcpServers.other.url, 'https://example.invalid');
  assert.deepEqual(parseJson(result).mcpServers.repograph, entry);
  assert.equal(mergeJson(result, 'mcpServers', entry), result);
});

test('malformed, duplicate, non-object, and conflicting JSON fail before modification', () => {
  for (const text of ['{"oops":', '[]', '{"mcpServers":null}', '{"mcpServers":{},"mcpServers":{}}', '{"mcpServers":{"repograph":{"url":"https://other.invalid"}}}']) {
    assert.throws(() => mergeJson(text, 'mcpServers', entry));
  }
});

test('Codex merge preserves TOML comments and configuration including literal strings', () => {
  const before = '# retain\nmodel = "example"\n[projects."C:/project"]\ntrust_level = "trusted"\n[mcp_servers.other]\ncommand = \'/other/tool\'\n';
  const result = mergeToml(before, entry);
  assert.ok(result.startsWith(before));
  assert.equal(parseToml(result).model, 'example');
  assert.equal(parseToml(result).projects['C:/project'].trust_level, 'trusted');
  assert.deepEqual({ ...parseToml(result).mcp_servers.repograph }, entry);
  assert.equal(mergeToml(result, entry), result);
  assert.throws(() => mergeToml('[mcp_servers.repograph]\ncommand="other"\n', entry), /different/);
  assert.throws(() => mergeToml('mcp_servers = { other = { command = "other" } }\n', entry), /Cannot extend/);
});

test('all four project layouts install the full skill and leave execution disabled', t => {
  const root = fixture(t);
  const python = path.join(root, 'trusted-runtime', 'python');
  const writes = planSetup(root, Object.keys(AGENTS), python, skill);
  assert.ok(writes.length > 0);
  assert.equal(fs.readdirSync(root).length, 0, 'preparation must not write');
  applySetup(writes);
  for (const [agent, spec] of Object.entries(AGENTS)) {
    assert.equal(fs.readFileSync(path.join(root, spec.skill, 'references/setup.md'), 'utf8'), 'Setup\n');
    const config = fs.readFileSync(path.join(root, spec.config), 'utf8');
    const result = agent === 'codex' ? parseToml(config).mcp_servers.repograph : parseJson(config)[spec.key].repograph;
    assert.equal(result.command, python);
    assert.deepEqual(result.args, ['-I', '-m', 'repograph', '--root', root, 'serve']);
    assert.ok(!config.includes('--enable-verification'));
  }
  assert.deepEqual(planSetup(root, Object.keys(AGENTS), python, skill), []);
});

test('customized skill prevents every project write', t => {
  const root = fixture(t);
  fs.mkdirSync(path.join(root, '.cursor/skills/repograph'), { recursive: true });
  const custom = path.join(root, '.cursor/skills/repograph/SKILL.md');
  fs.writeFileSync(custom, 'my custom instructions');
  assert.throws(() => planSetup(root, ['cursor'], '/python', skill), /Existing skill file differs/);
  assert.equal(fs.readFileSync(custom, 'utf8'), 'my custom instructions');
  assert.ok(!fs.existsSync(path.join(root, '.cursor/mcp.json')));
});

test('destination junctions/symlinks and escaping paths are rejected', t => {
  const root = fixture(t);
  const outside = fixture(t);
  try { fs.symlinkSync(outside, path.join(root, '.cursor'), process.platform === 'win32' ? 'junction' : 'dir'); }
  catch (error) { if (error.code === 'EPERM') { t.skip('Host does not permit directory links'); return; } throw error; }
  assert.throws(() => planSetup(root, ['cursor'], '/python', skill), /symlink/);
  assert.throws(() => projectPath(root, '../outside'), /inside/);
  assert.deepEqual(fs.readdirSync(outside), []);
});

test('concurrent config edits are detected before applying the plan', t => {
  const root = fixture(t);
  const plan = planSetup(root, ['claude-code'], '/python', skill);
  fs.writeFileSync(path.join(root, '.mcp.json'), '{"changed":true}');
  assert.throws(() => applySetup(plan), /changed during setup/);
  assert.equal(fs.readFileSync(path.join(root, '.mcp.json'), 'utf8'), '{"changed":true}');
  assert.ok(!fs.existsSync(path.join(root, '.claude')));
});

test('a failed file replacement restores previously changed config', t => {
  const root = fixture(t);
  const config = path.join(root, '.mcp.json');
  const original = '{"mcpServers":{"other":{"command":"tool"}}}';
  fs.writeFileSync(config, original);
  const plan = planSetup(root, ['claude-code'], '/python', skill);
  const rename = fs.renameSync;
  let count = 0;
  const handle = mock.method(fs, 'renameSync', (...args) => {
    if (++count === 2) throw new Error('simulated disk error');
    return rename(...args);
  });
  try { assert.throws(() => applySetup(plan), /simulated disk error/); }
  finally { handle.mock.restore(); }
  assert.equal(fs.readFileSync(config, 'utf8'), original);
  assert.ok(!fs.existsSync(path.join(root, '.claude/skills/repograph/SKILL.md')));
});
