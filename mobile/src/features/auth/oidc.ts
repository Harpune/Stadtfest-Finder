/**
 * OIDC Authorization Code + PKCE against the IdP via expo-auth-session (system browser sheet).
 * The app never sees passwords; the hosted login handles sign-up, reset and validation.
 */
import * as AuthSession from 'expo-auth-session';

import {
  AUTH_CLIENT_ID,
  AUTH_ISSUER,
  LoginMethod,
  authorizeOptions,
  redirectUri,
} from './config';
import {SessionExpiredError} from './session';
import type {TokenSet} from './tokens';

let discovery: Promise<AuthSession.DiscoveryDocument> | null = null;

function loadDiscovery(): Promise<AuthSession.DiscoveryDocument> {
  if (!discovery) {
    discovery = AuthSession.fetchDiscoveryAsync(AUTH_ISSUER).catch(error => {
      discovery = null; // retry on the next attempt
      throw error;
    });
  }
  return discovery;
}

function toTokenSet(response: AuthSession.TokenResponse): TokenSet {
  const issuedAt = (response.issuedAt ?? Math.floor(Date.now() / 1000)) * 1000;
  return {
    accessToken: response.accessToken,
    refreshToken: response.refreshToken ?? null,
    idToken: response.idToken ?? null,
    expiresAt: issuedAt + (response.expiresIn ?? 300) * 1000,
  };
}

export type LoginResult =
  {type: 'success'; tokens: TokenSet} | {type: 'cancel'} | {type: 'error'};

/**
 * Runs the login in the browser sheet and exchanges the code for tokens.
 *
 * `isAborted` is asked right before the browser opens: if the user has left the entry
 * screen while the login was being prepared (slow network), no browser pops up later.
 */
export async function loginWithIdp(
  method: LoginMethod,
  isAborted?: () => boolean,
): Promise<LoginResult> {
  try {
    const document = await loadDiscovery();
    const {scopes, extraParams} = authorizeOptions(method);
    const request = new AuthSession.AuthRequest({
      clientId: AUTH_CLIENT_ID,
      redirectUri: redirectUri(),
      scopes,
      extraParams,
      usePKCE: true,
    });
    // Prepares PKCE and state up front, so the check below sits directly before the prompt.
    await request.makeAuthUrlAsync(document);
    if (isAborted?.()) return {type: 'cancel'};
    const result = await request.promptAsync(document);
    if (result.type === 'cancel' || result.type === 'dismiss') {
      return {type: 'cancel'};
    }
    if (result.type !== 'success' || !result.params.code) {
      return {type: 'error'};
    }
    const response = await AuthSession.exchangeCodeAsync(
      {
        clientId: AUTH_CLIENT_ID,
        redirectUri: request.redirectUri,
        code: result.params.code,
        extraParams: {code_verifier: request.codeVerifier ?? ''},
      },
      document,
    );
    return {type: 'success', tokens: toTokenSet(response)};
  } catch {
    return {type: 'error'};
  }
}

/** Refresher for the session: rejected refresh tokens end the session. */
export async function refreshTokens(refreshToken: string): Promise<TokenSet> {
  const document = await loadDiscovery();
  try {
    const response = await AuthSession.refreshAsync(
      {clientId: AUTH_CLIENT_ID, refreshToken},
      document,
    );
    return toTokenSet(response);
  } catch (error) {
    // TokenError carries the OAuth error code (e.g. invalid_grant); network errors do not.
    if (error instanceof AuthSession.TokenError) {
      throw new SessionExpiredError();
    }
    throw error;
  }
}

/** Revokes the refresh token at the IdP (best effort on logout). */
export async function revokeRefreshToken(refreshToken: string): Promise<void> {
  try {
    const document = await loadDiscovery();
    if (!document.revocationEndpoint) return;
    await AuthSession.revokeAsync(
      {
        clientId: AUTH_CLIENT_ID,
        token: refreshToken,
        tokenTypeHint: AuthSession.TokenTypeHint.RefreshToken,
      },
      document,
    );
  } catch {
    // Logout must not fail because the IdP is unreachable; local tokens are deleted anyway.
  }
}
