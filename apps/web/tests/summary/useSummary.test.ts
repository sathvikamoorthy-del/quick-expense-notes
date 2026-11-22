/** @jest-environment node */
import { createApiClient } from '../../src/api/client';
import { fetchSummary } from '../../src/summary/useSummary';

type Call = { url: string; method: string };
const fakeApi = (status: number, body: unknown) => {
  const calls: Call[] = [];
  const fetchImpl = (async (input: Request) => {
    calls.push({ url: input.url, method: input.method });
    return new Response(JSON.stringify(body), { status, headers: { 'Content-Type': 'application/json' } });
  }) as unknown as typeof fetch;
  return { calls, client: createApiClient('http://api.test', fetchImpl) };
};

const november = {
  month: '2026-11',
  current_month: '2026-11',
  categories: [{ code: 'F', category: 'Food', total: '590.00', total_paise: 59000 }],
  grand_total: '590.00',
  grand_total_paise: 59000,
};

describe('fetchSummary', () => {
  it('asks for the current month with no month parameter', async () => {
    const f = fakeApi(200, november);
    await expect(fetchSummary(null, f.client)).resolves.toEqual(november);
    expect(f.calls).toEqual([{ url: 'http://api.test/summary', method: 'GET' }]);
  });

  it('asks for a given month', async () => {
    const f = fakeApi(200, { ...november, month: '2026-10', categories: [], grand_total: '0.00', grand_total_paise: 0 });
    await fetchSummary('2026-10', f.client);
    expect(f.calls).toEqual([{ url: 'http://api.test/summary?month=2026-10', method: 'GET' }]);
  });

  it('throws the API error code, or the status, when the request fails', async () => {
    await expect(fetchSummary('2027-01', fakeApi(422, { error: 'validation-error' }).client)).rejects.toThrow('validation-error');
    await expect(fetchSummary(null, fakeApi(500, {}).client)).rejects.toThrow('request failed (500)');
  });
});
