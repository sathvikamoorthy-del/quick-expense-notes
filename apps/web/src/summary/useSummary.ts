// Asks the API for the monthly summary (REQ-279). The totals are computed by the API from the saved entries; this only
// fetches them.
import { api } from '../api/client';
import type { components } from '../api/schema';
import type { ApiClient } from '../entries/useExpand';
import { useAsync } from '../state/useAsync';

export type SummaryResponse = components['schemas']['SummaryResponse'];

/** Calls GET /summary; `month` is `YYYY-MM`, or null for the current IST month (decided by the API). */
export async function fetchSummary(month: string | null, client: ApiClient = api): Promise<SummaryResponse> {
  const init = month === null ? {} : { params: { query: { month } } };
  const { data, error, response } = await client.GET('/summary', init);
  if (data) return data;
  const message = (error as { error?: unknown } | undefined)?.error;
  throw new Error(typeof message === 'string' ? message : `request failed (${response.status})`);
}

export function useSummary(month: string | null, client: ApiClient = api) {
  return useAsync<SummaryResponse>(() => fetchSummary(month, client), [month, client]);
}
