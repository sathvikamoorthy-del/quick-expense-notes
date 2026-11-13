/** @jest-environment node */
import { createApiClient } from '../../src/api/client';
import { expandEntry } from '../../src/entries/useExpand';

type Call = { url: string; method: string; body: unknown };
const fakeApi = (status: number, body: unknown) => {
  const calls: Call[] = [];
  const fetchImpl = (async (input: Request) => {
    calls.push({ url: input.url, method: input.method, body: await input.json() });
    return new Response(JSON.stringify(body), { status, headers: { 'Content-Type': 'application/json' } });
  }) as unknown as typeof fetch;
  return { calls, client: createApiClient('http://api.test', fetchImpl) };
};

const entry = { code: 'SWG', merchant: 'Swiggy', category: 'Food', amount: '340.00', amount_paise: 34000, date: '2026-11-11', note: null };

describe('expandEntry', () => {
  it('posts the text as typed and returns the expanded entry', async () => {
    const f = fakeApi(200, { ok: true, entry, error: null });
    await expect(expandEntry('swg 340 yd', f.client)).resolves.toEqual({ ok: true, entry, error: null });
    expect(f.calls).toEqual([{ url: 'http://api.test/entries/expand', method: 'POST', body: { text: 'swg 340 yd' } }]);
  });

  it('returns a rule error as a normal answer', async () => {
    const f = fakeApi(200, { ok: false, entry: null, error: 'Unknown code "X".' });
    await expect(expandEntry('X 100', f.client)).resolves.toEqual({ ok: false, entry: null, error: 'Unknown code "X".' });
  });

  it('throws the API error code when the request fails', async () => {
    await expect(expandEntry('F 250', fakeApi(401, { error: 'unauthorized' }).client)).rejects.toThrow('unauthorized');
  });

  it('throws the status when the failure has no error code', async () => {
    await expect(expandEntry('F 250', fakeApi(500, {}).client)).rejects.toThrow('request failed (500)');
  });
});
