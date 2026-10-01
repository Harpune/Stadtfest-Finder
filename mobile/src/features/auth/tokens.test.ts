import {readIdTokenClaims, secureTokenStore} from './tokens';

function idToken(payload: object): string {
  const json = JSON.stringify(payload);
  const bytes = encodeURIComponent(json).replace(/%([0-9A-F]{2})/g, (_, hex) =>
    String.fromCharCode(parseInt(hex, 16)),
  );
  const base64 = btoa(bytes)
    .replace(/\+/g, '-')
    .replace(/\//g, '_')
    .replace(/=+$/, '');
  return `header.${base64}.signature`;
}

describe('readIdTokenClaims', () => {
  it('reads email and names including umlauts', () => {
    const claims = readIdTokenClaims(
      idToken({
        email: 'jürgen@example.test',
        given_name: 'Jürgen',
        family_name: 'Größ',
      }),
    );
    expect(claims).toEqual({
      email: 'jürgen@example.test',
      given_name: 'Jürgen',
      family_name: 'Größ',
    });
  });

  it('returns nothing for missing or malformed tokens', () => {
    expect(readIdTokenClaims(null)).toEqual({});
    expect(readIdTokenClaims('garbage')).toEqual({});
  });
});

describe('secureTokenStore', () => {
  beforeEach(() => secureTokenStore.clear());

  it('round-trips tokens through secure storage', async () => {
    const tokens = {
      accessToken: 'at',
      refreshToken: 'rt',
      idToken: null,
      expiresAt: 123,
    };
    await secureTokenStore.save(tokens);
    expect(await secureTokenStore.load()).toEqual(tokens);
    await secureTokenStore.clear();
    expect(await secureTokenStore.load()).toBeNull();
  });
});
