// Root jobs and the unprivileged sync job have separate status directories.
import fs from 'node:fs';
import path from 'node:path';

export const syncStatusDir = () => path.join(process.env.FEWZHUN_BOX_STATE_DIR || '/var/lib/fewzhun-box', 'status');

export function readJobs(root) {
  const jobs = {};
  const dir = path.join(root, 'status');
  let files = [];
  try { files = fs.readdirSync(dir).filter((f) => f.endsWith('.json')).sort(); } catch { /* not readable */ }
  for (const file of files) {
    try { jobs[file.slice(0, -5)] = JSON.parse(fs.readFileSync(path.join(dir, file), 'utf8')); } catch { /* not readable */ }
  }
  try {
    const sync = JSON.parse(fs.readFileSync(path.join(syncStatusDir(), 'sync.json'), 'utf8'));
    // A root failure alert can be newer than sync's last status (for example after a crash).
    if (!jobs.sync || !(Date.parse(jobs.sync.ts) > Date.parse(sync.ts))) jobs.sync = sync;
  } catch { /* no sync yet */ }
  return jobs;
}
