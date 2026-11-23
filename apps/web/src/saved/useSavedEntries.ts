// The saved-entries list, editing one entry (REQ-280) and deleting one (REQ-281). The API applies the rules; this only sends the text as typed.
import { api } from '../api/client';
import type { components } from '../api/schema';
import type { ApiClient } from '../entries/useExpand';
import { useAsync } from '../state/useAsync';

export type SavedEntriesResponse = components['schemas']['SavedEntriesResponse'];
export type SavedEntry = components['schemas']['SavedEntry'];
export type EditResponse = components['schemas']['EditResponse'];

function failure(error: unknown, status: number): Error {
  const message = (error as { error?: unknown } | undefined)?.error;
  return new Error(typeof message === 'string' ? message : `request failed (${status})`);
}

/** Calls GET /entries; `month` is `YYYY-MM`, or null for the current IST month (decided by the API). */
export async function fetchSavedEntries(month: string | null, client: ApiClient = api): Promise<SavedEntriesResponse> {
  const init = month === null ? {} : { params: { query: { month } } };
  const { data, error, response } = await client.GET('/entries', init);
  if (data) return data;
  throw failure(error, response.status);
}

/** Calls PUT /entries/{id}. A refused edit is a normal answer (ok: false); only a failed request throws. */
export async function editEntry(id: string, text: string, client: ApiClient = api): Promise<EditResponse> {
  const { data, error, response } = await client.PUT('/entries/{expense_id}', {
    params: { path: { expense_id: id } },
    body: { text },
  });
  if (data) return data;
  throw failure(error, response.status);
}

/** Calls DELETE /entries/{id} (REQ-281: final, no undo). Resolves when deleted; throws the API error code otherwise. */
export async function deleteEntry(id: string, client: ApiClient = api): Promise<void> {
  const { error, response } = await client.DELETE('/entries/{expense_id}', { params: { path: { expense_id: id } } });
  if (response.ok) return;
  throw failure(error, response.status);
}

export function useSavedEntries(month: string | null, client: ApiClient = api) {
  return useAsync<SavedEntriesResponse>(() => fetchSavedEntries(month, client), [month, client]);
}
