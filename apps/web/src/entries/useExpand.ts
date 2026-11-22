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

export type ExpandAllResponse = components['schemas']['ExpandAllResponse'];
export type ExpandResult = components['schemas']['ExpandResult'];

/**
 * Calls POST /entries/expand-all with a whole text box (REQ-277). The API splits it into entries; this sends it as typed.
 * Too many entries or an entry's rule error is a normal answer (ok: false); only a failed request throws.
 */
export async function expandAll(text: string, client: ApiClient = api): Promise<ExpandAllResponse> {
  const { data, error, response } = await client.POST('/entries/expand-all', { body: { text } });
  if (data) return data;
  const message = (error as { error?: unknown } | undefined)?.error;
  throw new Error(typeof message === 'string' ? message : `request failed (${response.status})`);
}

export type SaveResponse = components['schemas']['SaveResponse'];

/**
 * Calls POST /entries/save (REQ-278) with the text box and the review the user saw (the `results` of expandAll,
 * unchanged). The API expands the text again and refuses when it differs; a refusal is data, only a failed request throws.
 */
export async function saveEntries(text: string, reviewed: ExpandResult[], client: ApiClient = api): Promise<SaveResponse> {
  const { data, error, response } = await client.POST('/entries/save', { body: { text, reviewed } });
  if (data) return data;
  const message = (error as { error?: unknown } | undefined)?.error;
  throw new Error(typeof message === 'string' ? message : `request failed (${response.status})`);
}

/** Like useExpand, for a whole text box. A new `request` number expands the same text again (e.g. after a refused save). */
export function useExpandAll(text: string | null, client: ApiClient = api, request = 0) {
  return useAsync<ExpandAllResponse | null>(
    () => (text === null ? Promise.resolve(null) : expandAll(text, client)),
    [text, client, request],
  );
}
