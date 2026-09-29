import {createAuthFetch, Session, SessionExpiredError} from './session';
import type {TokenSet, TokenStore} from './tokens';

const NOW = 1_000_000;

function tokens(accessToken: string, expiresIn = 300_000): TokenSet {
  return {
    accessToken,
    refreshToken: `refresh-${accessToken}`,
    idToken: null,
    expiresAt: NOW + expiresIn,
  };
}

function memoryStore(initial: TokenSet | null = null) {
  let saved = initial;
  const store: TokenStore & {saved: () => TokenSet | null} = {
    load: async () => saved,
    save: async value => {
      saved = value;
    },
    clear: async () => {
      saved = null;
    },
    saved: () => saved,
  };
  return store;
}

function recordingFetch(acceptedToken: string) {
  const seen: (string | null)[] = [];
  const fetch = jest.fn(async (request: Request) => {
    const header = request.headers.get('Authorization');
    seen.push(header);
    const ok = header === `Bearer ${acceptedToken}`;
    return new Response(ok ? '{}' : '', {status: ok ? 200 : 401});
  });
  return {fetch, seen};
}

describe('Session', () => {
  it('sends the access token of a valid session', async () => {
    const session = new Session({
      refresh: jest.fn(),
      store: memoryStore(tokens('a1')),
      now: () => NOW,
    });
    await session.restore();
    const {fetch, seen} = recordingFetch('a1');

    const response = await createAuthFetch(
      session,
      fetch,
    )(new Request('http://api.test/v1/me'));

    expect(response.status).toBe(200);
    expect(seen).toEqual(['Bearer a1']);
  });

  it('passes guest requests through without a token', async () => {
    const session = new Session({refresh: jest.fn(), store: memoryStore()});
    await session.restore();
    const {fetch, seen} = recordingFetch('x');

    await createAuthFetch(
      session,
      fetch,
    )(new Request('http://api.test/v1/events'));

    expect(seen).toEqual([null]);
  });

  it('renews an expiring token once for parallel requests', async () => {
    const refresh = jest.fn(async () => tokens('a2'));
    const session = new Session({
      refresh,
      store: memoryStore(tokens('a1', 10_000)),
      now: () => NOW,
    });
    await session.restore();
    const {fetch, seen} = recordingFetch('a2');
    const authFetch = createAuthFetch(session, fetch);

    const responses = await Promise.all(
      [1, 2, 3].map(() => authFetch(new Request('http://api.test/v1/me'))),
    );

    expect(refresh).toHaveBeenCalledTimes(1);
    expect(refresh).toHaveBeenCalledWith('refresh-a1');
    expect(responses.map(r => r.status)).toEqual([200, 200, 200]);
    expect(seen).toEqual(['Bearer a2', 'Bearer a2', 'Bearer a2']);
  });

  it('renews on 401 and repeats the request with its body', async () => {
    const refresh = jest.fn(async () => tokens('a2'));
    const store = memoryStore(tokens('a1'));
    const session = new Session({refresh, store, now: () => NOW});
    await session.restore();
    const bodies: string[] = [];
    const fetch = jest.fn(async (request: Request) => {
      bodies.push(await request.text());
      const ok = request.headers.get('Authorization') === 'Bearer a2';
      return new Response('', {status: ok ? 200 : 401});
    });

    const response = await createAuthFetch(
      session,
      fetch,
    )(new Request('http://api.test/v1/me', {method: 'PATCH', body: '{"a":1}'}));

    expect(response.status).toBe(200);
    expect(bodies).toEqual(['{"a":1}', '{"a":1}']);
    expect(store.saved()?.accessToken).toBe('a2');
    expect(store.saved()?.refreshToken).toBe('refresh-a2');
  });

  it('ends the session when the refresh token is rejected', async () => {
    const store = memoryStore(tokens('a1'));
    const session = new Session({
      refresh: jest.fn(async () => {
        throw new SessionExpiredError();
      }),
      store,
      now: () => NOW,
    });
    await session.restore();
    const expired = jest.fn();
    session.onExpired(expired);
    const {fetch} = recordingFetch('never');

    const response = await createAuthFetch(
      session,
      fetch,
    )(new Request('http://api.test/v1/me'));

    expect(response.status).toBe(401);
    expect(expired).toHaveBeenCalledTimes(1);
    expect(session.current).toBeNull();
    expect(store.saved()).toBeNull();
  });

  it('keeps the session when the IdP is unreachable', async () => {
    const store = memoryStore(tokens('a1', 1_000));
    const session = new Session({
      refresh: jest.fn(async () => {
        throw new TypeError('Network request failed');
      }),
      store,
      now: () => NOW,
    });
    await session.restore();
    const expired = jest.fn();
    session.onExpired(expired);

    expect(await session.accessToken()).toBeNull();
    expect(expired).not.toHaveBeenCalled();
    expect(store.saved()?.accessToken).toBe('a1');
  });

  it('does not renew twice if another request already renewed', async () => {
    const refresh = jest.fn(async () => tokens('a2'));
    const session = new Session({
      refresh,
      store: memoryStore(tokens('a1')),
      now: () => NOW,
    });
    await session.restore();

    expect(await session.renew('a1')).toBe('a2');
    expect(await session.renew('a1')).toBe('a2');
    expect(refresh).toHaveBeenCalledTimes(1);
  });
});
