/** Test helpers for auth: fake IdP gateway, fake API responses and a provider wrapper. */
import {QueryClient, QueryClientProvider} from '@tanstack/react-query';
import * as AuthSession from 'expo-auth-session';
import React, {PropsWithChildren} from 'react';

import {AuthGateway, AuthProvider, Me} from './AuthProvider';
import {authSession} from './authSession';
import type {LoginMethod} from './config';
import type {LoginResult} from './oidc';
import type {TokenSet} from './tokens';

export const LENA: Me = {
  id: '00000000-0000-0000-0000-000000000001',
  firstName: 'Lena',
  lastName: 'Beispiel',
  roles: ['user'],
};

function base64Url(value: string): string {
  return btoa(value).replace(/\+/g, '-').replace(/\//g, '_').replace(/=+$/, '');
}

export function testTokens(
  accessToken = 'at-1',
  expiresIn = 300_000,
): TokenSet {
  const payload = base64Url(JSON.stringify({email: 'lena@example.test'}));
  return {
    accessToken,
    refreshToken: `rt-${accessToken}`,
    idToken: `h.${payload}.s`,
    expiresAt: Date.now() + expiresIn,
  };
}

export function fakeGateway(
  result: LoginResult = {type: 'success', tokens: testTokens()},
) {
  const gateway = {
    session: authSession,
    login: jest.fn<Promise<LoginResult>, [LoginMethod, (() => boolean)?]>(
      async () => result,
    ),
    revoke: jest.fn(async () => undefined),
  } satisfies AuthGateway;
  return gateway;
}

export interface ApiCall {
  method: string;
  path: string;
  authorization: string | null;
  body: string;
}

/** Answers /v1/me and /v1/me/favorites like the backend; everything else with an empty list. */
export function mockMeApi(
  options: {
    me?: Me;
    status?: number;
    favoriteStatus?: number;
    unread?: number;
  } = {},
) {
  const calls: ApiCall[] = [];
  let me = options.me ?? LENA;
  jest.spyOn(global, 'fetch').mockImplementation(async input => {
    const request = input as Request;
    const url = new URL(request.url);
    const body = await request.text();
    calls.push({
      method: request.method,
      path: url.pathname,
      authorization: request.headers.get('Authorization'),
      body,
    });
    const json = (value: unknown, status = 200) =>
      new Response(JSON.stringify(value), {
        status,
        headers: {'Content-Type': 'application/json'},
      });
    if (url.pathname === '/v1/me/notifications') {
      return new Response(JSON.stringify({items: []}), {
        headers: {
          'Content-Type': 'application/json',
          'X-Unread-Count': String(options.unread ?? 0),
        },
      });
    }
    if (url.pathname.startsWith('/v1/me/favorites')) {
      if (request.method === 'GET') return json({items: []});
      return new Response(null, {status: options.favoriteStatus ?? 204});
    }
    if (url.pathname !== '/v1/me') return json([]);
    if (options.status && options.status !== 200) {
      return json({error: 'x', message: 'x'}, options.status);
    }
    if (request.method === 'DELETE') return new Response(null, {status: 204});
    if (request.method === 'PATCH') me = {...me, ...JSON.parse(body)};
    return json(me);
  });
  return calls;
}

/** Makes the next token renewal fail as rejected (invalid_grant). */
export function rejectRefresh() {
  jest
    .mocked(AuthSession.refreshAsync)
    .mockRejectedValue(new AuthSession.TokenError({error: 'invalid_grant'}));
}

export async function resetAuth() {
  await authSession.end();
  (
    globalThis as {mockSecureStore?: Map<string, string>}
  ).mockSecureStore?.clear();
}

export function AuthTestProviders({
  children,
  gateway,
}: PropsWithChildren<{gateway: AuthGateway}>) {
  const [client] = React.useState(
    () => new QueryClient({defaultOptions: {queries: {retry: false}}}),
  );
  return (
    <QueryClientProvider client={client}>
      <AuthProvider gateway={gateway}>{children}</AuthProvider>
    </QueryClientProvider>
  );
}
