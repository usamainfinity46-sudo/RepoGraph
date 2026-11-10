import assert from 'node:assert/strict';
import fs from 'node:fs';
import os from 'node:os';
import path from 'node:path';
import crypto from 'node:crypto';
import { test } from 'node:test';
import { loadRelease, runtimePaths, runtimeReady, ensureRuntime } from '../lib/runtime.mjs';

const hash = value => crypto.createHash('sha256').update(value).digest('hex');

function fixture(t) {
  const root = fs.realpathSync(fs.mkdtempSync(path.join(os.tmpdir(), 'kit-payload-test-')));
  t.after(() => fs.rmSync(root, { recursive: true, force: true }));
  const payload = path.join(root, 'payload');
  fs.mkdirSync(payload);
  const release = { serverVersion: '0.1.0rc2', wheel: 'repograph_mcp-0.1.0rc2-py3-none-any.whl', sha256: hash('wheel'), requirementsSha256: hash('lock'), skillFiles: {} };
  fs.writeFileSync(path.join(payload, release.wheel), 'wheel');
  fs.writeFileSync(path.join(payload, 'requirements.lock'), 'lock');
  for (const name of ['SKILL.md', 'LICENSE', 'NOTICE', 'agents/openai.yaml', 'references/setup.md', 'references/verification.md', 'references/examples.md']) {
    const file = path.join(payload, 'skill', name);
    fs.mkdirSync(path.dirname(file), { recursive: true });
    fs.writeFileSync(file, name);
    release.skillFiles[name] = hash(name);
  }
  fs.writeFileSync(path.join(payload, 'release.json'), JSON.stringify(release));
  return { root, payload, release };
}

test('wheel, dependency lock and every skill file must match the release manifest', t => {
  const { root, payload, release } = fixture(t);
  assert.equal(Object.keys(loadRelease(root).skillFiles).length, 7);
  fs.writeFileSync(path.join(payload, 'requirements.lock'), 'modified');
  assert.throws(() => loadRelease(root), /dependency lock checksum/);
  fs.writeFileSync(path.join(payload, 'requirements.lock'), 'lock');
  fs.writeFileSync(path.join(payload, 'skill/SKILL.md'), 'modified');
  assert.throws(() => loadRelease(root), /skill checksum/);
  fs.writeFileSync(path.join(payload, 'skill/SKILL.md'), 'SKILL.md');
  fs.writeFileSync(path.join(payload, release.wheel), 'modified');
  assert.throws(() => loadRelease(root), /wheel checksum/);
});

test('manifest paths cannot select arbitrary files', t => {
  const { root, payload, release } = fixture(t);
  delete release.skillFiles['SKILL.md'];
  release.skillFiles['../outside'] = hash('outside');
  fs.writeFileSync(path.join(payload, 'release.json'), JSON.stringify(release));
  assert.throws(() => loadRelease(root), /Skill manifest/);
});

test('runtime identity changes with locked dependencies; incomplete environments are not ready', t => {
  const { root, release } = fixture(t);
  const runtime = runtimePaths(root, release);
  assert.notEqual(runtime.directory, runtimePaths(root, { ...release, requirementsSha256: hash('different lock') }).directory);
  assert.equal(runtimeReady(runtime, release), false);
  fs.mkdirSync(path.dirname(runtime.python), { recursive: true });
  fs.writeFileSync(runtime.python, 'not executed by readiness check');
  assert.equal(runtimeReady(runtime, release), false);
  assert.throws(() => ensureRuntime(runtime, release, root), /incomplete or foreign/);
  fs.writeFileSync(path.join(runtime.directory, 'repograph-kit.json'), JSON.stringify({ sha256: release.sha256, requirementsSha256: release.requirementsSha256 }));
  assert.equal(runtimeReady(runtime, release), true);
});
