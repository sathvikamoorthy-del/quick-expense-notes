// Generates src/api/schema.d.ts from the API's OpenAPI document (openapi-typescript).
//   node scripts/generate-client.cjs [openapi.json]          write the types
//   node scripts/generate-client.cjs --check [openapi.json]  fail when the committed types are stale
// The document defaults to OPENAPI_PATH or ../api/openapi.json (in the API app: python scripts/tasks.py openapi).
'use strict';
const { execFileSync } = require('node:child_process');
const fs = require('node:fs');
const os = require('node:os');
const path = require('node:path');

const OUTPUT = 'src/api/schema.d.ts';

/** node_modules/.bin/openapi-typescript in the app or, when dependencies are hoisted, in a parent folder. */
function findBin(from) {
  const name = process.platform === 'win32' ? 'openapi-typescript.cmd' : 'openapi-typescript';
  for (let dir = from; ; dir = path.dirname(dir)) {
    const candidate = path.join(dir, 'node_modules', '.bin', name);
    if (fs.existsSync(candidate)) return candidate;
    if (path.dirname(dir) === dir) return null;
  }
}

/** Returns { code, message }: 0 on success. Never exits the process, so it can be tested. */
function generate({ args = [], cwd = process.cwd(), env = process.env } = {}) {
  const check = args.includes('--check');
  const input = path.resolve(cwd, args.find((a) => !a.startsWith('--')) ?? env.OPENAPI_PATH ?? '../api/openapi.json');
  const output = path.resolve(cwd, OUTPUT);
  const bin = findBin(cwd);
  if (!fs.existsSync(input)) return { code: 1, message: `OpenAPI document not found: ${input} (in the API app run: python scripts/tasks.py openapi)` };
  if (!bin) return { code: 1, message: 'openapi-typescript is not installed: run npm install' };

  const scratch = check ? fs.mkdtempSync(path.join(os.tmpdir(), 'knm-client-')) : null;
  const target = scratch ? path.join(scratch, 'schema.d.ts') : output;
  try {
    fs.mkdirSync(path.dirname(output), { recursive: true });
    // Run the package's JS entry with node: Windows refuses to spawn the .bin/*.cmd shim without a shell (Node EINVAL).
    const cli = path.join(path.dirname(path.dirname(bin)), 'openapi-typescript', 'bin', 'cli.js');
    execFileSync(process.execPath, [cli, input, '-o', target], { stdio: 'pipe', cwd });
    if (!check) return { code: 0, message: `wrote ${OUTPUT} from ${input}` };
    const fresh = fs.readFileSync(target, 'utf8');
    const current = fs.existsSync(output) ? fs.readFileSync(output, 'utf8') : '';
    if (fresh !== current) return { code: 1, message: `${OUTPUT} is stale: the API schema changed. Run: node scripts/generate-client.cjs` };
    return { code: 0, message: `${OUTPUT} matches ${input}` };
  } catch (e) {
    return { code: 1, message: `openapi-typescript failed: ${String(e.stderr || e.message).slice(0, 500)}` };
  } finally {
    if (scratch) fs.rmSync(scratch, { recursive: true, force: true });
  }
}

module.exports = { generate };

if (require.main === module) {
  const { code, message } = generate({ args: process.argv.slice(2) });
  (code ? console.error : console.log)(message);
  process.exit(code);
}
