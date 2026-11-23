/** @jest-environment node */
import { createApiClient } from '../../src/api/client';
import { editEntry, fetchSavedEntries } from '../../src/saved/useSavedEntries';

type Call = { url: string; method: string; body: unknown };
const fakeApi = (status: number, body: unknown) => {
  const calls: Call[] = [];
  const fetchImpl = (async (input: Request) => {
    const text = await input.text();
    calls.push({ url: input.url, method: input.method, body: text ? JSON.parse(text) : null });
    return new Response(JSON.stringify(body), { status, headers: { 'Content-Type': 'application/json' } });
  }) as unknown as typeof fetch;
  return { calls, client: createApiClient('http://api.test', fetchImpl) };
};

const entry = {
  id: '00000000-0000-0000-0000-000000000001',
  typed: 'UBR 220 12/11 airport',
  code: 'UBR',
  merchant: 'Uber',
  category: 'Travel',
  amount: '220.00',
  amount_paise: 22000,
  date: '2026-11-12',
  note: 'airport',
};
const list = { month: '2026-11', current_month: '2026-11', entries: [entry] };

describe('fetchSavedEntries', () => {
  it('asks for the current month with no month parameter, then a given month', async () => {
    const f = fakeApi(200, list);
    await expect(fetchSavedEntries(null, f.client)).resolves.toEqual(list);
    await fetchSavedEntries('2026-10', f.client);
    expect(f.calls.map((c) => [c.method, c.url])).toEqual([
      ['GET', 'http://api.test/entries'],
      ['GET', 'http://api.test/entries?month=2026-10'],
    ]);
  });

  it('throws the API error code when the request fails', async () => {
    await expect(fetchSavedEntries('2027-01', fakeApi(422, { error: 'validation-error' }).client)).rejects.toThrow('validation-error');
  });
});

describe('editEntry', () => {
  it('puts the text as typed to the entry and returns the updated entry', async () => {
    const reply = { ok: true, error: null, entry };
    const f = fakeApi(200, reply);
    await expect(editEntry(entry.id, 'UBR 220 12/11 airport', f.client)).resolves.toEqual(reply);
    expect(f.calls).toEqual([
      { url: `http://api.test/entries/${entry.id}`, method: 'PUT', body: { text: 'UBR 220 12/11 airport' } },
    ]);
  });

  it('returns a refused edit as a normal answer', async () => {
    const refused = { ok: false, error: 'Unknown code "X".', entry: null };
    await expect(editEntry(entry.id, 'X 100', fakeApi(200, refused).client)).resolves.toEqual(refused);
  });

  it('throws the API error code, or the status, when the request fails', async () => {
    await expect(editEntry('nope', 'F 1', fakeApi(404, { error: 'not-found' }).client)).rejects.toThrow('not-found');
    await expect(editEntry('nope', 'F 1', fakeApi(500, {}).client)).rejects.toThrow('request failed (500)');
  });
});
