import {authorizeOptions} from './config';

describe('authorizeOptions', () => {
  it('adds the Keycloak IdP hint for social logins', () => {
    expect(authorizeOptions('google', 'keycloak').extraParams).toEqual({
      kc_idp_hint: 'google',
    });
  });

  it('uses the Zitadel IdP scope for social logins', () => {
    const {scopes, extraParams} = authorizeOptions('apple', 'zitadel');
    expect(scopes).toContain('urn:zitadel:iam:org:idp:id:apple');
    expect(scopes).toContain('urn:zitadel:iam:org:projects:roles');
    expect(extraParams).toEqual({});
  });

  it('opens the registration for "Konto erstellen"', () => {
    expect(authorizeOptions('register', 'keycloak').extraParams).toEqual({
      prompt: 'create',
    });
  });

  it('always requests a refresh token', () => {
    expect(authorizeOptions('email', 'keycloak').scopes).toContain(
      'offline_access',
    );
  });
});
