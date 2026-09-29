/**
 * OIDC configuration of the app (flow B, ADR 0003). Keycloak locally, Zitadel in production;
 * all values come from EXPO_PUBLIC_* variables at build time (mobile/.env.example).
 */
import * as AuthSession from 'expo-auth-session';

export type IdpKind = 'keycloak' | 'zitadel';

/** Issuer URL; must be reachable from the device and match AUTH_ISSUER of the backend. */
export const AUTH_ISSUER =
  process.env.EXPO_PUBLIC_AUTH_ISSUER ||
  'http://localhost:58080/realms/stadtfest';

export const AUTH_CLIENT_ID =
  process.env.EXPO_PUBLIC_AUTH_CLIENT_ID || 'stadtfest-app';

export const IDP_KIND: IdpKind =
  process.env.EXPO_PUBLIC_AUTH_IDP === 'zitadel' ? 'zitadel' : 'keycloak';

/** Identity provider IDs (Zitadel) or aliases (Keycloak) of the social logins. */
export const SOCIAL_IDPS = {
  apple: process.env.EXPO_PUBLIC_AUTH_APPLE_IDP || 'apple',
  google: process.env.EXPO_PUBLIC_AUTH_GOOGLE_IDP || 'google',
} as const;

/** `offline_access` yields a long-lived refresh token for silent renewal. */
export const AUTH_SCOPES = ['openid', 'profile', 'email', 'offline_access'];

/** Redirect back into the app: `stadtfest://auth` (registered at the IdP). */
export function redirectUri(): string {
  return AuthSession.makeRedirectUri({scheme: 'stadtfest', path: 'auth'});
}

/** How the user starts the login on the entry screen (R05-US1). */
export type LoginMethod = 'apple' | 'google' | 'email' | 'register';

export interface AuthorizeOptions {
  scopes: string[];
  extraParams: Record<string, string>;
}

/**
 * Scopes and parameters per login method: social logins carry an IdP hint so the hosted
 * login jumps straight to Apple/Google; "Konto erstellen" opens the registration.
 */
export function authorizeOptions(
  method: LoginMethod,
  kind: IdpKind = IDP_KIND,
): AuthorizeOptions {
  const scopes = [...AUTH_SCOPES];
  const extraParams: Record<string, string> = {};
  if (method === 'apple' || method === 'google') {
    const idp = SOCIAL_IDPS[method];
    if (kind === 'keycloak') {
      extraParams.kc_idp_hint = idp;
    } else {
      scopes.push(`urn:zitadel:iam:org:idp:id:${idp}`);
    }
  } else if (method === 'register') {
    extraParams.prompt = 'create';
  } else {
    extraParams.prompt = 'login';
  }
  if (kind === 'zitadel') {
    // Adds the project (= API audience) to the access token; roles are asserted by the
    // project setting "Assert Roles on Authentication" (00-docs/40-operations/zitadel.md).
    const projectId = process.env.EXPO_PUBLIC_AUTH_PROJECT_ID;
    if (projectId) {
      scopes.push(`urn:zitadel:iam:org:project:id:${projectId}:aud`);
    }
  }
  return {scopes, extraParams};
}
