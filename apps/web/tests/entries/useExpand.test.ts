/** @jest-environment node */
import { createApiClient } from '../../src/api/client';
import { expandAll, expandEntry, saveEntries } from '../../src/entries/useExpand';

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

describe('expandAll', () => {
  const text = 'F 250; SWG 340 yd\nX 100';
  const reply = {
    ok: true,
    error: null,
    results: [
      { typed: 'F 250', ok: true, entry: { ...entry, code: 'F', merchant: null, amount: '250.00', amount_paise: 25000 }, error: null },
      { typed: 'SWG 340 yd', ok: true, entry, error: null },
      { typed: 'X 100', ok: false, entry: null, error: 'Unknown code "X".' },
    ],
  };

  it('posts the whole text box unchanged and returns one result per entry', async () => {
    const f = fakeApi(200, reply);
    await expect(expandAll(text, f.client)).resolves.toEqual(reply);
    expect(f.calls).toEqual([{ url: 'http://api.test/entries/expand-all', method: 'POST', body: { text } }]);
  });

  it('returns a rejected text box as a normal answer', async () => {
    const rejected = { ok: false, error: 'Too many entries (max 20).', results: [] };
    await expect(expandAll(text, fakeApi(200, rejected).client)).resolves.toEqual(rejected);
  });

  it('throws the API error code, or the status, when the request fails', async () => {
    await expect(expandAll(text, fakeApi(422, { error: 'validation-error' }).client)).rejects.toThrow('validation-error');
    await expect(expandAll(text, fakeApi(500, {}).client)).rejects.toThrow('request failed (500)');
  });
});

describe('saveEntries', () => {
  const reviewed = [{ typed: 'SWG 340 yd', ok: true, entry, error: null }];

  it('posts the text and the review unchanged and returns the saved count', async () => {
    const reply = { ok: true, error: null, saved: 1, ids: ['id-1'], failed: [] };
    const f = fakeApi(200, reply);
    await expect(saveEntries('SWG 340 yd', reviewed, f.client)).resolves.toEqual(reply);
    expect(f.calls).toEqual([{ url: 'http://api.test/entries/save', method: 'POST', body: { text: 'SWG 340 yd', reviewed } }]);
  });

  it('returns a refused save as a normal answer', async () => {
    const refused = { ok: false, error: 'The entries changed since the review. Press Expand to review them again.', saved: 0, ids: [], failed: [] };
    await expect(saveEntries('SWG 340 yd', reviewed, fakeApi(200, refused).client)).resolves.toEqual(refused);
  });

  it('throws the API error code, or the status, when the request fails', async () => {
    await expect(saveEntries('SWG 340 yd', reviewed, fakeApi(401, { error: 'unauthorized' }).client)).rejects.toThrow('unauthorized');
    await expect(saveEntries('SWG 340 yd', reviewed, fakeApi(500, {}).client)).rejects.toThrow('request failed (500)');
  });
});
