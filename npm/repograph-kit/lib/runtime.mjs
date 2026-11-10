import fs from 'node:fs';
import path from 'node:path';
import os from 'node:os';
import crypto from 'node:crypto';
import { spawnSync } from 'node:child_process';

const SKILL_FILES = ['LICENSE', 'NOTICE', 'SKILL.md', 'agents/openai.yaml', 'references/examples.md', 'references/setup.md', 'references/verification.md'];

export function loadRelease(packageRoot) {
  const payload = path.join(packageRoot, 'payload');
  let release;
  try { release = JSON.parse(fs.readFileSync(path.join(payload, 'release.json'), 'utf8')); }
  catch { throw new Error('Release payload is missing or invalid. Install the published package or build its tarball first.'); }
  if (!/^repograph_mcp-[0-9a-z.]+-py3-none-any\.whl$/.test(release.wheel)
      || !/^[a-f0-9]{64}$/.test(release.sha256) || !/^[a-f0-9]{64}$/.test(release.requirementsSha256)
      || !/^\d+\.\d+\.\d+(?:rc\d+)?$/.test(release.serverVersion)) {
    throw new Error('Release manifest is invalid');
  }
  const wheel = path.join(payload, release.wheel);
  const actual = crypto.createHash('sha256').update(fs.readFileSync(wheel)).digest('hex');
  if (actual !== release.sha256) throw new Error('Bundled server wheel checksum mismatch');
  const requirements = path.join(payload, 'requirements.lock');
  if (crypto.createHash('sha256').update(fs.readFileSync(requirements)).digest('hex') !== release.requirementsSha256) {
    throw new Error('Bundled dependency lock checksum mismatch');
  }
  const skillFiles = {};
  if (!release.skillFiles || JSON.stringify(Object.keys(release.skillFiles).sort()) !== JSON.stringify(SKILL_FILES)) throw new Error('Skill manifest is invalid');
  for (const [name, hash] of Object.entries(release.skillFiles)) {
    if (!/^[a-zA-Z0-9_./-]+$/.test(name) || name.split('/').some(p => p === '..' || !p) || path.isAbsolute(name)) {
      throw new Error('Skill manifest path is invalid');
    }
    const file = path.join(payload, 'skill', name);
    const bytes = fs.readFileSync(file);
    if (crypto.createHash('sha256').update(bytes).digest('hex') !== hash) throw new Error('Bundled skill checksum mismatch');
    skillFiles[name] = bytes;
  }
  return { ...release, wheel, requirements, skillFiles };
}

export function defaultCache() {
  if (process.platform === 'win32') return path.join(process.env.LOCALAPPDATA || path.join(os.homedir(), 'AppData/Local'), 'repograph-kit');
  return path.join(process.env.XDG_CACHE_HOME || path.join(os.homedir(), '.cache'), 'repograph-kit');
}

export function runtimePaths(cache, release) {
  const key = crypto.createHash('sha256').update(release.sha256 + release.requirementsSha256).digest('hex').slice(0, 16);
  const directory = path.resolve(cache, `server-${release.serverVersion}-${key}`);
  return { directory, python: path.join(directory, process.platform === 'win32' ? 'Scripts/python.exe' : 'bin/python') };
}

function cleanEnvironment() {
  return Object.fromEntries(Object.entries(process.env).filter(([key]) => !/^(UV_|PIP_|PYTHON|VIRTUAL_ENV$)/i.test(key)));
}

function findExecutable(name, projectRoot) {
  for (const directory of (process.env.PATH || '').split(path.delimiter).filter(Boolean)) {
    for (const extension of process.platform === 'win32' ? ['.exe', '.EXE'] : ['']) {
      const candidate = path.resolve(directory, name + extension);
      try {
        const real = fs.realpathSync(candidate);
        const relative = path.relative(projectRoot, real);
        if (!relative.startsWith('..' + path.sep) && !path.isAbsolute(relative)) continue;
        if (/[/\\]Microsoft[/\\]WindowsApps[/\\]/i.test(real)) continue;
        fs.accessSync(real, fs.constants.X_OK);
        return real;
      } catch { /* Try another installed host executable. */ }
    }
  }
  return null;
}

function run(command, args, options = {}) {
  const result = spawnSync(command, args, { shell: false, env: cleanEnvironment(), timeout: 300_000, stdio: 'inherit', ...options });
  if (result.error || result.status !== 0) throw new Error('Backend setup failed; no agent files were changed. Check the tool output above.');
  return result;
}

export function runtimeReady(runtime, release) {
  try {
    const marker = JSON.parse(fs.readFileSync(path.join(runtime.directory, 'repograph-kit.json'), 'utf8'));
    return marker.sha256 === release.sha256 && marker.requirementsSha256 === release.requirementsSha256 && fs.existsSync(runtime.python);
  } catch { return false; }
}

export function ensureRuntime(runtime, release, projectRoot) {
  if (runtimeReady(runtime, release)) return;
  // Reject pre-existing incomplete/foreign environments rather than executing or replacing them.
  if (fs.existsSync(runtime.directory)) throw new Error('Backend cache is incomplete or foreign; select a fresh --cache-dir');
  fs.mkdirSync(path.dirname(runtime.directory), { recursive: true, mode: 0o700 });
  const uv = findExecutable('uv', projectRoot);
  if (uv) {
    run(uv, ['--no-config', 'venv', '--python', '3.12', runtime.directory]);
    run(uv, ['--no-config', 'pip', 'install', '--python', runtime.python, '--require-hashes', '--only-binary', ':all:', '--index-url', 'https://pypi.org/simple', '-r', release.requirements]);
    run(uv, ['--no-config', 'pip', 'install', '--python', runtime.python, '--no-deps', release.wheel]);
  } else {
    let python;
    for (const name of process.platform === 'win32' ? ['python', 'python3', 'py'] : ['python3', 'python']) {
      const executable = findExecutable(name, projectRoot);
      if (!executable) continue;
      const args = [...(name === 'py' ? ['-3'] : []), '-I', '-c', 'import sys,json; print(json.dumps([sys.executable,list(sys.version_info[:2])]))'];
      const probe = spawnSync(executable, args, { shell: false, env: cleanEnvironment(), encoding: 'utf8', timeout: 10_000 });
      try {
        const [location, version] = JSON.parse(probe.stdout);
        if (probe.status === 0 && version[0] === 3 && version[1] >= 11 && version[1] <= 13) { python = location; break; }
      } catch { /* Not a supported interpreter. */ }
    }
    if (!python) throw new Error('Install uv (https://docs.astral.sh/uv/) or Python 3.11-3.13, then rerun setup.');
    run(python, ['-I', '-m', 'venv', runtime.directory]);
    run(runtime.python, ['-I', '-m', 'pip', '--isolated', 'install', '--require-hashes', '--only-binary=:all:', '--index-url', 'https://pypi.org/simple', '-r', release.requirements]);
    run(runtime.python, ['-I', '-m', 'pip', '--isolated', 'install', '--no-deps', release.wheel]);
  }
  const result = run(runtime.python, ['-I', '-c', 'import repograph; print(repograph.__version__)'], { stdio: 'pipe', encoding: 'utf8' });
  if (result.stdout.trim() !== release.serverVersion) throw new Error('Installed backend version differs from the bundled release');
  fs.writeFileSync(path.join(runtime.directory, 'repograph-kit.json'), JSON.stringify({ sha256: release.sha256, requirementsSha256: release.requirementsSha256 }), { flag: 'wx', mode: 0o600 });
}
