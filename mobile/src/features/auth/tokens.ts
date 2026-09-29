/**
 * Token set of the signed-in user and its secure persistence. Tokens live only in
 * expo-secure-store (Keychain/Keystore), never in AsyncStorage (R05-US2).
 */
import * as SecureStore from 'expo-secure-store';

export interface TokenSet {
  accessToken: string;
  refreshToken: string | null;
  idToken: string | null;
  /** Expiry of the access token in epoch milliseconds. */
  expiresAt: number;
}

export interface TokenStore {
  load(): Promise<TokenSet | null>;
  save(tokens: TokenSet): Promise<void>;
  clear(): Promise<void>;
}

// One key per token: some Android keystores warn about values larger than 2 KB.
const KEYS = {
  accessToken: 'auth.accessToken',
  refreshToken: 'auth.refreshToken',
  idToken: 'auth.idToken',
  expiresAt: 'auth.expiresAt',
} as const;

const OPTIONS: SecureStore.SecureStoreOptions = {
  keychainAccessible: SecureStore.AFTER_FIRST_UNLOCK_THIS_DEVICE_ONLY,
};

export const secureTokenStore: TokenStore = {
  async load() {
    const [accessToken, refreshToken, idToken, expiresAt] = await Promise.all([
      SecureStore.getItemAsync(KEYS.accessToken, OPTIONS),
      SecureStore.getItemAsync(KEYS.refreshToken, OPTIONS),
      SecureStore.getItemAsync(KEYS.idToken, OPTIONS),
      SecureStore.getItemAsync(KEYS.expiresAt, OPTIONS),
    ]);
    if (!accessToken || !expiresAt) return null;
    return {
      accessToken,
      refreshToken: refreshToken ?? null,
      idToken: idToken ?? null,
      expiresAt: Number(expiresAt),
    };
  },
  async save(tokens) {
    await Promise.all([
      SecureStore.setItemAsync(KEYS.accessToken, tokens.accessToken, OPTIONS),
      SecureStore.setItemAsync(
        KEYS.expiresAt,
        String(tokens.expiresAt),
        OPTIONS,
      ),
      tokens.refreshToken
        ? SecureStore.setItemAsync(
            KEYS.refreshToken,
            tokens.refreshToken,
            OPTIONS,
          )
        : SecureStore.deleteItemAsync(KEYS.refreshToken, OPTIONS),
      tokens.idToken
        ? SecureStore.setItemAsync(KEYS.idToken, tokens.idToken, OPTIONS)
        : SecureStore.deleteItemAsync(KEYS.idToken, OPTIONS),
    ]);
  },
  async clear() {
    await Promise.all(
      Object.values(KEYS).map(key => SecureStore.deleteItemAsync(key, OPTIONS)),
    );
  },
};

export interface IdTokenClaims {
  email?: string;
  given_name?: string;
  family_name?: string;
}

function base64UrlDecode(value: string): string {
  const base64 = value.replace(/-/g, '+').replace(/_/g, '/');
  const padded = base64 + '='.repeat((4 - (base64.length % 4)) % 4);
  const binary = atob(padded);
  // UTF-8 bytes -> string (names with umlauts).
  const percentEncoded = Array.from(
    binary,
    ch => `%${ch.charCodeAt(0).toString(16).padStart(2, '0')}`,
  ).join('');
  return decodeURIComponent(percentEncoded);
}

/**
 * Reads display claims (email, names) from the ID token. The token comes straight from the
 * IdP's token endpoint over TLS, so the signature is not checked here; the backend never
 * trusts these values.
 */
export function readIdTokenClaims(idToken: string | null): IdTokenClaims {
  if (!idToken) return {};
  try {
    const payload = JSON.parse(base64UrlDecode(idToken.split('.')[1] ?? ''));
    return {
      email: typeof payload.email === 'string' ? payload.email : undefined,
      given_name:
        typeof payload.given_name === 'string' ? payload.given_name : undefined,
      family_name:
        typeof payload.family_name === 'string'
          ? payload.family_name
          : undefined,
    };
  } catch {
    return {};
  }
}
