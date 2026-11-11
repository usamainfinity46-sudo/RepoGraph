// Trusted reporter for Node 22/24. Never loads repository reporters or configs.
// NDJSON preserves file evidence that older built-in JUnit reporters omit.
export default async function* report(source) {
  yield JSON.stringify({ type: 'header', schema: 1 }) + '\n';
  const parents = new Map();
  let outcomes = 0;
  let overflow = false;
  for await (const event of source) {
    const data = event.data || {};
    if (event.type === 'test:start') {
      if (parents.size < 5000 || parents.has(data.file)) {
        const chain = parents.get(data.file) || [];
        if (Number.isInteger(data.nesting) && data.nesting >= 0 && data.nesting < 100) {
          chain[data.nesting] = String(data.name).slice(0, 4000);
          chain.length = data.nesting + 1;
          parents.set(data.file, chain);
        }
      }
    } else if (event.type === 'test:pass' || event.type === 'test:fail') {
      const details = data.details || {};
      if (details.type === 'suite') {
        if (event.type === 'test:fail' && details.error?.failureType !== 'subtestsFailed') {
          yield JSON.stringify({ type: 'suite_error', message: String(details.error?.message || 'Suite failed').slice(0, 4000) }) + '\n';
        }
        continue;
      }
      if (++outcomes > 5000) {
        if (!overflow) yield JSON.stringify({ type: 'error', message: 'Test case limit exceeded' }) + '\n';
        overflow = true;
        continue;
      }
      const classname = data.classname || details.classname || (parents.get(data.file) || []).slice(0, data.nesting).join(' > ');
      yield JSON.stringify({
        type: 'case', name: String(data.name).slice(0, 4000), file: data.entryFile || data.file,
        classname: String(classname).slice(0, 4000),
        status: data.skip || data.todo ? 'skipped' : event.type === 'test:pass' ? 'passed' : 'failed',
        synthetic: data.name === data.file && data.nesting === 0 && data.line === 1 && data.column === 1,
        message: String(details.error?.message || '').slice(0, 4000),
      }) + '\n';
    } else if (event.type === 'test:summary' && !data.file) {
      yield JSON.stringify({ type: 'summary', counts: data.counts, success: data.success }) + '\n';
    }
  }
}
