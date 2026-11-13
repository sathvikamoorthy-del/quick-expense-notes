/** @jest-environment node */
import { spawnSync } from 'child_process';
import fs from 'fs';
import os from 'os';
import path from 'path';
// Adapted import: the script is plain CommonJS without type declarations (TS7016 under strict mode).
// eslint-disable-next-line @typescript-eslint/no-var-requires
const { generate } = require('../../../../scripts/generate-client.cjs') as { generate: (o: { args: string[]; cwd: string; env: Record<string, string> }) => { code: number; [k: string]: unknown } };

// Runs in a scratch app that shares this project's node_modules (openapi-typescript).
const SCRIPT = path.resolve(__dirname, '../../../../scripts/generate-client.cjs');
const nodeModules = (() => { let d = __dirname; while (!fs.existsSync(path.join(d, 'node_modules/.bin/openapi-typescript'))) { const up = path.dirname(d); if (up === d) throw new Error('openapi-typescript is not installed'); d = up; } return path.join(d, 'node_modules'); })();

const doc = (paths: Record<string, unknown>) => JSON.stringify({ openapi: '3.1.0', info: { title: 't', version: '1' }, paths }, null, 2);
const ping = { '/ping': { get: { operationId: 'ping', responses: { '200': { description: 'ok', content: { 'application/json': { schema: { type: 'object', properties: { ok: { type: 'boolean' } } } } } } } } } };
const users = { ...ping, '/users': { get: { operationId: 'users', responses: { '200': { description: 'ok' } } } } };

let app: string;
beforeEach(() => { app = fs.mkdtempSync(path.join(os.tmpdir(), 'knm-gen-')); fs.symlinkSync(nodeModules, path.join(app, 'node_modules'), 'junction'); }); // adapted setup: a junction needs no admin rights on Windows ('dir' symlinks do)
afterEach(() => fs.rmSync(app, { recursive: true, force: true }));
const run = (...args: string[]) => generate({ args, cwd: app, env: {} });
const write = (name: string, text: string) => fs.writeFileSync(path.join(app, name), text);
const schema = () => fs.readFileSync(path.join(app, 'src/api/schema.d.ts'), 'utf8');

describe('generate-client contract', () => {
  it('writes src/api/schema.d.ts with the API paths', () => {
    write('openapi.json', doc(ping));
    expect(run('openapi.json').code).toBe(0);
    expect(schema()).toMatch(/"\/ping"/);
  });

  it('--check passes when the types match the document and fails when the API schema changed', () => {
    write('openapi.json', doc(ping));
    expect(run('openapi.json').code).toBe(0);
    expect(run('--check', 'openapi.json').code).toBe(0);
    write('openapi.json', doc(users));
    const stale = run('--check', 'openapi.json');
    expect(stale.code).toBe(1);
    expect(stale.message).toMatch(/stale/);
    expect(run('openapi.json').code).toBe(0);                      // regenerating fixes it
    expect(run('--check', 'openapi.json').code).toBe(0);
  });

  it('--check does not modify the committed types and fails when there are none yet', () => {
    write('openapi.json', doc(ping));
    expect(run('--check', 'openapi.json').code).toBe(1);
    expect(fs.existsSync(path.join(app, 'src/api/schema.d.ts'))).toBe(false);
    run('openapi.json');
    const before = schema();
    write('openapi.json', doc(users));
    run('--check', 'openapi.json');
    expect(schema()).toBe(before);
  });

  it('uses OPENAPI_PATH when no document is given, and explains a missing one', () => {
    write('spec.json', doc(ping));
    expect(generate({ args: [], cwd: app, env: { OPENAPI_PATH: 'spec.json' } }).code).toBe(0);
    const missing = run('nope.json');
    expect(missing.code).toBe(1);
    expect(missing.message).toMatch(/OpenAPI document not found/);
  });

  it('reports a document openapi-typescript cannot read, and a missing install', () => {
    write('bad.json', '{ not json');
    const bad = run('bad.json');
    expect(bad.code).toBe(1);
    expect(bad.message).toMatch(/openapi-typescript failed/);
    fs.unlinkSync(path.join(app, 'node_modules'));
    write('openapi.json', doc(ping));
    expect(run('openapi.json').message).toMatch(/not installed/);
  });

  it('works as a command: exit code and message', () => {
    write('openapi.json', doc(ping));
    const r = spawnSync('node', [SCRIPT, 'openapi.json'], { cwd: app, encoding: 'utf8' });
    expect(r.status).toBe(0);
    expect(r.stdout).toMatch(/wrote src\/api\/schema.d.ts/);
    write('openapi.json', doc(users));
    const stale = spawnSync('node', [SCRIPT, '--check', 'openapi.json'], { cwd: app, encoding: 'utf8' });
    expect(stale.status).toBe(1);
    expect(stale.stderr).toMatch(/stale/);
  });
});
