import * as AuthSession from 'expo-auth-session';

import {loginWithIdp} from './oidc';

function mockRequest(result: {type: string; params?: Record<string, string>}) {
  const request = {
    redirectUri: 'stadtfest://auth',
    codeVerifier: 'verifier',
    makeAuthUrlAsync: jest.fn(async () => 'http://idp.test/auth?x=1'),
    promptAsync: jest.fn(async () => result),
  };
  jest.mocked(AuthSession.AuthRequest).mockImplementation(
    // The mock only needs the members loginWithIdp uses.
    () => request as unknown as AuthSession.AuthRequest,
  );
  return request;
}

describe('loginWithIdp', () => {
  afterEach(() => jest.clearAllMocks());

  it('exchanges the code for tokens after a successful prompt', async () => {
    const request = mockRequest({type: 'success', params: {code: 'c1'}});
    jest.mocked(AuthSession.exchangeCodeAsync).mockResolvedValue({
      accessToken: 'at',
      refreshToken: 'rt',
      idToken: 'id',
      issuedAt: 1000,
      expiresIn: 300,
    } as AuthSession.TokenResponse);

    const result = await loginWithIdp('email', () => false);

    expect(request.promptAsync).toHaveBeenCalled();
    expect(result).toEqual({
      type: 'success',
      tokens: {
        accessToken: 'at',
        refreshToken: 'rt',
        idToken: 'id',
        expiresAt: 1_300_000,
      },
    });
  });

  it('does not open the browser when the login was aborted meanwhile', async () => {
    const request = mockRequest({type: 'success', params: {code: 'c1'}});

    const result = await loginWithIdp('email', () => true);

    expect(result).toEqual({type: 'cancel'});
    expect(request.makeAuthUrlAsync).toHaveBeenCalled();
    expect(request.promptAsync).not.toHaveBeenCalled();
    expect(AuthSession.exchangeCodeAsync).not.toHaveBeenCalled();
  });

  it('reports a dismissed browser as cancel', async () => {
    mockRequest({type: 'dismiss'});
    expect(await loginWithIdp('email')).toEqual({type: 'cancel'});
  });
});
