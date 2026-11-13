// Typed API client over the generated schema (openapi-fetch). The bearer token is kept in memory only.
import createClient, { type Middleware } from 'openapi-fetch';
import type { paths } from './schema';

let token: string | null = null;
/** Sets (or, with null, clears) the bearer token sent with every request. In memory only: a reload signs the user out. */
export const setAuthToken = (value: string | null): void => { token = value; };
export const getAuthToken = (): string | null => token;

const auth: Middleware = {
  onRequest({ request }) {
    if (token) request.headers.set('Authorization', `Bearer ${token}`);
    return request;
  }
};

/** In development `/api` is proxied to the API (see API_PROXY_TARGET); in production serve the API under /api or pass its URL. */
export function createApiClient(baseUrl = '/api', fetchImpl?: typeof fetch) {
  const client = createClient<paths>({ baseUrl, ...(fetchImpl ? { fetch: fetchImpl } : {}) });
  client.use(auth);
  return client;
}

export const api = createApiClient();
