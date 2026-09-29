/** Process-wide session instance used by the API client and the AuthProvider. */
import {refreshTokens} from './oidc';
import {createAuthFetch, Session} from './session';
import {secureTokenStore} from './tokens';

export const authSession = new Session({
  refresh: refreshTokens,
  store: secureTokenStore,
});

/** Fetch with bearer token and silent renewal; resolves fetch per call so tests can mock it. */
export const authFetch = createAuthFetch(authSession, request =>
  globalThis.fetch(request),
);
