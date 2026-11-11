import { spawnSync } from 'node:child_process';
import { inspectConfiguration, managedOptions } from './config.mjs';

export function projectReadiness(runtime, root, flags = []) {
  const result = spawnSync(runtime.python, ['-I', '-m', 'repograph', '--root', root, ...flags, 'doctor'], {
    shell: false, encoding: 'utf8', timeout: 60_000, maxBuffer: 4_000_000,
    env: Object.fromEntries(Object.entries(process.env).filter(([key]) => !/^(PYTHON|VIRTUAL_ENV$)/i.test(key))),
  });
  if (result.error || ![0, 1].includes(result.status)) throw new Error('Project preflight failed; run the installed backend doctor command for details.');
  try { return JSON.parse(result.stdout); }
  catch { throw new Error('Backend doctor returned an invalid report'); }
}

export function configurationReport(root, python) {
  return Object.fromEntries(Object.entries(inspectConfiguration(root)).map(([agent, status]) => {
    const flags = status.entry ? managedOptions(status.entry, root, [python]) : null;
    return [agent, { configured: status.configured, currentBackend: flags !== null,
      verificationEnabled: flags?.includes('--enable-verification') || false,
      ...(status.error ? { error: status.error } : {}) }];
  }));
}

export function readinessText(report) {
  const lines = [
    `Source preflight: ${report.ready_for_indexing ? 'ready for indexing' : 'needs attention'} (${report.source_files} files). This is not a successful index.`,
    `Git: ${report.git_status}. Tests: ${report.tests_found}; runners: ${report.test_frameworks.join(', ') || 'not identified'}.`,
    `RepoGraph test execution: ${report.verification_enabled ? 'enabled; each prepared command still needs approval' : 'disabled; analysis and recommendations remain available'}.`,
  ];
  if (!report.verification_enabled) lines.push('To opt in: rerun setup --agent AGENT --upgrade --enable-verification. For pytest, also set --python-executable to your project interpreter.');
  for (const diagnostic of report.diagnostics.slice(0, 8)) lines.push(`${diagnostic.code}${diagnostic.path ? ` (${diagnostic.path})` : ''}: ${diagnostic.message}`);
  if (report.diagnostics.length > 8) lines.push('Run doctor --json for the bounded diagnostic list.');
  return lines.join('\n');
}
