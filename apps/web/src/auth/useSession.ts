// The signed-in user (REQ-275). Kept in memory only, like the token in the API client: a page refresh signs the user out.
// The sign-in rules live in the API; this module only sends what was typed and keeps the answer.
import { api, createApiClient, setAuthToken, setUnauthorizedHandler } from '../api/client';
import type { components } from '../api/schema';
import { createAppStore } from '../state/createStore';

export type SignedInUser = components['schemas']['SignedInUser'];
export type ApiClient = ReturnType<typeof createApiClient>;
export type SignInResult = { ok: true } | { ok: false; error: string };

export const INVALID_CREDENTIALS = 'Invalid email or password.';
export const SIGN_IN_FAILED = 'Could not sign in. Try again.';

// not persisted: no key and no storage, so nothing survives a page refresh
export const useSession = createAppStore<{ user: SignedInUser | null }>({ user: null }, { storage: null });

/** Forgets the token and the user; the guarded pages then show the Sign in screen. */
export function signOut(): void {
  setAuthToken(null);
  useSession.getState().reset();
}

/** Calls POST /auth/sign-in. An empty email or password is answered here, with the same message, without a request. */
export async function signIn(email: string, password: string, client: ApiClient = api): Promise<SignInResult> {
  if (!email.trim() || !password.trim()) return { ok: false, error: INVALID_CREDENTIALS };
  try {
    const { data, response } = await client.POST('/auth/sign-in', { body: { email, password } });
    if (data) {
      setAuthToken(data.token);
      useSession.setState({ user: data.user });
      return { ok: true };
    }
    return { ok: false, error: response.status === 401 ? INVALID_CREDENTIALS : SIGN_IN_FAILED };
  } catch {
    return { ok: false, error: SIGN_IN_FAILED };
  }
}

// an expired token (401 on any request that carried it) signs the user out
setUnauthorizedHandler(signOut);
