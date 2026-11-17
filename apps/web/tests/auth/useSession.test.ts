/** @jest-environment node */
// The real API client (node has fetch Request), the in-memory session and the sign-out on 401 (REQ-275).
import fs from 'fs';
import path from 'path';
import { createApiClient, getAuthToken } from '../../src/api/client';
import { INVALID_CREDENTIALS, SIGN_IN_FAILED, signIn, signOut, useSession } from '../../src/auth/useSession';

const user = { id: 'u-1', email: 'asha@example.com', display_name: 'Asha' };
const json = (body: unknown, status = 200) => new Response(JSON.stringify(body), { status, headers: { 'Content-Type': 'application/json' } });

function fakeApi(replies: Response[]) {
  const calls: { url: string; auth: string | null }[] = [];
  const impl = (async (input: Request) => { calls.push({ url: input.url, auth: input.headers.get('Authorization') }); return replies.shift()!; }) as unknown as typeof fetch;
  return { calls, client: createApiClient('http://api.test', impl) };
}

afterEach(() => signOut());

describe('session', () => {
  it('signs in through the real client and keeps the token and user in memory', async () => {
    const api = fakeApi([json({ token: 'tok', expires_in: 3600, user })]);
    expect(await signIn('asha@example.com', 'correct-horse-1', api.client)).toEqual({ ok: true });
    expect(api.calls).toEqual([{ url: 'http://api.test/auth/sign-in', auth: null }]);
    expect(getAuthToken()).toBe('tok');
    expect(useSession.getState().user).toEqual(user);
  });

  it('a fresh page (module reload) starts signed out: nothing was stored', async () => {
    await signIn('asha@example.com', 'correct-horse-1', fakeApi([json({ token: 'tok', expires_in: 3600, user })]).client);
    jest.isolateModules(() => {
      const fresh = require('../../src/auth/useSession');
      const freshClient = require('../../src/api/client');
      expect(fresh.useSession.getState().user).toBeNull();
      expect(freshClient.getAuthToken()).toBeNull();
    });
    const source = fs.readFileSync(path.join(__dirname, '../../src/auth/useSession.ts'), 'utf8');
    expect(source).not.toMatch(/localStorage|sessionStorage|document\.cookie|indexedDB|persistKey:/);
  });

  it('signOut forgets the token and the user', async () => {
    await signIn('asha@example.com', 'correct-horse-1', fakeApi([json({ token: 'tok', expires_in: 3600, user })]).client);
    signOut();
    expect(getAuthToken()).toBeNull();
    expect(useSession.getState().user).toBeNull();
  });

  it('a 401 on a request that carried the token (expired) signs the user out', async () => {
    const api = fakeApi([json({ token: 'tok', expires_in: 3600, user }), json({ error: 'unauthorized' }, 401)]);
    await signIn('asha@example.com', 'correct-horse-1', api.client);
    await api.client.POST('/entries/expand', { body: { text: 'SWG 340 yd' } });
    expect(api.calls[1].auth).toBe('Bearer tok');
    expect(getAuthToken()).toBeNull();
    expect(useSession.getState().user).toBeNull();
  });

  it('wrong details give the shared message; other failures a retry message', async () => {
    expect(await signIn('asha@example.com', 'wrong-password', fakeApi([json({ error: INVALID_CREDENTIALS }, 401)]).client))
      .toEqual({ ok: false, error: INVALID_CREDENTIALS });
    expect(await signIn('asha@example.com', 'correct-horse-1', fakeApi([json({ error: 'internal-error' }, 500)]).client))
      .toEqual({ ok: false, error: SIGN_IN_FAILED });
    const down = createApiClient('http://api.test', (async () => { throw new TypeError('network'); }) as unknown as typeof fetch);
    expect(await signIn('asha@example.com', 'correct-horse-1', down)).toEqual({ ok: false, error: SIGN_IN_FAILED });
    expect(getAuthToken()).toBeNull();
  });

  it('an empty email or password is refused without a request', async () => {
    const api = fakeApi([]);
    expect(await signIn('  ', 'correct-horse-1', api.client)).toEqual({ ok: false, error: INVALID_CREDENTIALS });
    expect(await signIn('asha@example.com', '', api.client)).toEqual({ ok: false, error: INVALID_CREDENTIALS });
    expect(api.calls).toEqual([]);
  });
});
