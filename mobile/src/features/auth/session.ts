/**
 * Session of the signed-in user: holds the tokens, renews the access token silently and
 * makes parallel requests wait for a single renewal (R05-US4).
 */
import type {TokenSet, TokenStore} from './tokens';

/** Renew this long before the access token expires. */
const EXPIRY_MARGIN_MS = 30_000;

/** The refresh token was rejected (expired, revoked): the session is over. */
export class SessionExpiredError extends Error {
  constructor() {
    super('session expired');
    this.name = 'SessionExpiredError';
  }
}

/** Exchanges a refresh token for new tokens. Throws `SessionExpiredError` on rejection. */
export type Refresher = (refreshToken: string) => Promise<TokenSet>;

type Listener = () => void;

export interface SessionOptions {
  refresh: Refresher;
  store: TokenStore;
  now?: () => number;
}

export class Session {
  private tokens: TokenSet | null = null;
  private renewal: Promise<string | null> | null = null;
  private readonly expiredListeners = new Set<Listener>();
  private readonly refresh: Refresher;
  private readonly store: TokenStore;
  private readonly now: () => number;

  constructor({refresh, store, now = Date.now}: SessionOptions) {
    this.refresh = refresh;
    this.store = store;
    this.now = now;
  }

  /** Loads persisted tokens (app start). Returns true if a session exists. */
  async restore(): Promise<boolean> {
    this.tokens = await this.store.load();
    return this.tokens !== null;
  }

  get current(): TokenSet | null {
    return this.tokens;
  }

  async start(tokens: TokenSet): Promise<void> {
    this.tokens = tokens;
    await this.store.save(tokens);
  }

  /** Forgets all tokens locally (logout, account deletion, expired session). */
  async end(): Promise<void> {
    this.tokens = null;
    this.renewal = null;
    await this.store.clear();
  }

  /** Called when the session ends because renewal was rejected. */
  onExpired(listener: Listener): () => void {
    this.expiredListeners.add(listener);
    return () => this.expiredListeners.delete(listener);
  }

  /** A valid access token (renewed if it is about to expire), or null as guest/offline. */
  async accessToken(): Promise<string | null> {
    const tokens = this.tokens;
    if (!tokens) return null;
    if (tokens.expiresAt - EXPIRY_MARGIN_MS > this.now()) {
      return tokens.accessToken;
    }
    return this.renew(tokens.accessToken);
  }

  /**
   * Renews the access token once for all callers. `rejected` is the token the server
   * refused; if another request has already renewed it, the new token is returned directly.
   */
  async renew(rejected: string): Promise<string | null> {
    const tokens = this.tokens;
    if (!tokens) return null;
    if (tokens.accessToken !== rejected) return tokens.accessToken;
    if (!this.renewal) {
      this.renewal = this.performRenewal(tokens).finally(() => {
        this.renewal = null;
      });
    }
    return this.renewal;
  }

  private async performRenewal(tokens: TokenSet): Promise<string | null> {
    if (!tokens.refreshToken) {
      await this.expire();
      return null;
    }
    try {
      const renewed = await this.refresh(tokens.refreshToken);
      await this.start({
        ...renewed,
        // Some IdPs rotate refresh tokens only sometimes.
        refreshToken: renewed.refreshToken ?? tokens.refreshToken,
        idToken: renewed.idToken ?? tokens.idToken,
      });
      return renewed.accessToken;
    } catch (error) {
      if (error instanceof SessionExpiredError) {
        await this.expire();
      }
      // Network errors keep the session; the request goes out without a fresh token.
      return null;
    }
  }

  private async expire(): Promise<void> {
    await this.end();
    this.expiredListeners.forEach(listener => listener());
  }
}

/**
 * Wraps fetch: adds the bearer token and, on `401`, renews the token once and repeats the
 * request. Requests of guests pass through unchanged.
 */
export function createAuthFetch(
  session: Session,
  baseFetch: (request: Request) => Promise<Response>,
) {
  return async (request: Request): Promise<Response> => {
    const token = await session.accessToken();
    if (!token) return baseFetch(request);
    const retry = request.clone();
    const response = await baseFetch(withBearer(request, token));
    if (response.status !== 401) return response;
    const renewed = await session.renew(token);
    if (!renewed) return response;
    return baseFetch(withBearer(retry, renewed));
  };
}

function withBearer(request: Request, token: string): Request {
  const headers = new Headers(request.headers);
  headers.set('Authorization', `Bearer ${token}`);
  return new Request(request, {headers});
}
