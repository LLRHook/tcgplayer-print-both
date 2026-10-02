import { spawnSync } from 'node:child_process';
import { readdirSync } from 'node:fs';
const folder = new URL('../tests/', import.meta.url);
for (const file of readdirSync(folder).filter(x => x.endsWith('.mjs')).sort()) {
  const run = spawnSync(process.execPath, [new URL(file, folder).pathname], { stdio: 'inherit' });
  if (run.status !== 0) process.exit(run.status || 1);
}
