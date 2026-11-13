// Asks the API to expand one short entry (REQ-276). The rules live in the API only: this hook sends the text as typed.
import { api, createApiClient } from '../api/client';
import type { components } from '../api/schema';
import { useAsync } from '../state/useAsync';

export type ExpandResponse = components['schemas']['ExpandResponse'];
export type ExpandedEntry = components['schemas']['ExpandedEntry'];
export type ApiClient = ReturnType<typeof createApiClient>;

/** Calls POST /entries/expand. A rule error is a normal answer (ok: false); only a failed request throws. */
export async function expandEntry(text: string, client: ApiClient = api): Promise<ExpandResponse> {
  const { data, error, response } = await client.POST('/entries/expand', { body: { text } });
  if (data) return data;
  const message = (error as { error?: unknown } | undefined)?.error;
  throw new Error(typeof message === 'string' ? message : `request failed (${response.status})`);
}

/** Expands `text` whenever it changes; `null` means nothing was submitted yet (state stays success with null). */
export function useExpand(text: string | null, client: ApiClient = api) {
  return useAsync<ExpandResponse | null>(() => (text === null ? Promise.resolve(null) : expandEntry(text, client)), [text, client]);
}
