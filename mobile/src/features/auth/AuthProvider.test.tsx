import {fireEvent, screen, waitFor} from '@testing-library/react-native';
import {router} from 'expo-router';
import React from 'react';
import {Pressable, Text} from 'react-native';

import {renderWithProviders} from '@/test-utils';

import {AuthGateway, useAuth} from './AuthProvider';
import {authSession} from './authSession';
import {secureTokenStore} from './tokens';
import {
  AuthTestProviders,
  fakeGateway,
  mockMeApi,
  rejectRefresh,
  resetAuth,
  testTokens,
} from './testing';

let allowed: boolean | null = null;

function Probe() {
  const auth = useAuth();
  return (
    <>
      <Pressable
        testID="heart"
        onPress={() => {
          allowed = auth.requestAccountAction({
            type: 'favorite',
            eventId: 'e1',
          });
        }}
      />
      <Pressable
        testID="invite"
        onPress={() => {
          allowed = auth.requestAccountAction({type: 'invite', eventId: 'e2'});
        }}
      />
      <Pressable testID="login" onPress={() => auth.login('email')} />
      <Pressable testID="logout" onPress={() => auth.logout()} />
      <Text testID="status">{auth.status}</Text>
      <Text testID="user">{auth.user?.firstName ?? 'none'}</Text>
      <Text testID="email">{auth.email ?? 'none'}</Text>
      <Text testID="pending">
        {auth.pendingAction ? JSON.stringify(auth.pendingAction) : 'none'}
      </Text>
    </>
  );
}

async function renderProbe(gateway: AuthGateway = fakeGateway()) {
  await renderWithProviders(
    <AuthTestProviders gateway={gateway}>
      <Probe />
    </AuthTestProviders>,
  );
  await waitFor(() =>
    expect(screen.getByTestId('status')).not.toHaveTextContent('restoring'),
  );
}

beforeEach(async () => {
  await resetAuth();
  allowed = null;
  jest.clearAllMocks();
});

describe('AuthProvider guest hint', () => {
  it('remembers the action and shows the matching hint', async () => {
    mockMeApi();
    await renderProbe();
    await fireEvent.press(screen.getByTestId('heart'));
    expect(allowed).toBe(false);
    expect(screen.getByText('Lieblingsfeste merken')).toBeOnTheScreen();
    expect(screen.getByTestId('pending')).toHaveTextContent(
      JSON.stringify({type: 'favorite', eventId: 'e1'}),
    );
  });

  it('discards the pending action with "Weiter ohne Konto"', async () => {
    mockMeApi();
    await renderProbe();
    await fireEvent.press(screen.getByTestId('invite'));
    expect(screen.getByText('Freunde einladen')).toBeOnTheScreen();
    await fireEvent.press(screen.getByTestId('guestHint.dismiss'));
    expect(screen.getByTestId('pending')).toHaveTextContent('none');
  });

  it('opens the login entry screen and keeps the pending action', async () => {
    mockMeApi();
    await renderProbe();
    await fireEvent.press(screen.getByTestId('heart'));
    await fireEvent.press(screen.getByTestId('guestHint.login'));
    expect(router.push).toHaveBeenCalledWith('/login');
    expect(screen.getByTestId('pending')).not.toHaveTextContent('none');
  });
});

describe('AuthProvider login', () => {
  it('stores tokens, loads the profile and executes the pending favorite', async () => {
    const calls = mockMeApi();
    await renderProbe();
    await fireEvent.press(screen.getByTestId('heart'));

    await fireEvent.press(screen.getByTestId('login'));

    await waitFor(() =>
      expect(screen.getByTestId('status')).toHaveTextContent('signedIn'),
    );
    expect(
      await screen.findByText('Angemeldet · Fest gemerkt'),
    ).toBeOnTheScreen();
    expect(screen.getByTestId('pending')).toHaveTextContent('none');
    expect(screen.getByTestId('user')).toHaveTextContent('Lena');
    expect(screen.getByTestId('email')).toHaveTextContent('lena@example.test');
    expect(calls).toContainEqual(
      expect.objectContaining({
        method: 'GET',
        path: '/v1/me',
        authorization: 'Bearer at-1',
      }),
    );
    expect((await secureTokenStore.load())?.refreshToken).toBe('rt-at-1');
    // The heart tapped as a guest is set after the login (R06-US1).
    expect(calls).toContainEqual(
      expect.objectContaining({
        method: 'PUT',
        path: '/v1/me/favorites/e1',
        authorization: 'Bearer at-1',
      }),
    );
  });

  it('reports a failed pending favorite', async () => {
    mockMeApi({favoriteStatus: 500});
    await renderProbe();
    await fireEvent.press(screen.getByTestId('heart'));
    await fireEvent.press(screen.getByTestId('login'));
    expect(await screen.findByText('Das hat nicht geklappt')).toBeOnTheScreen();
  });

  it('welcomes the user by first name without pending action', async () => {
    mockMeApi();
    await renderProbe();
    await fireEvent.press(screen.getByTestId('login'));
    expect(await screen.findByText('Willkommen, Lena!')).toBeOnTheScreen();
  });

  it('opens the own invitation for a pending "Einladen"', async () => {
    mockMeApi();
    await renderProbe();
    await fireEvent.press(screen.getByTestId('invite'));
    await fireEvent.press(screen.getByTestId('login'));
    await waitFor(() =>
      expect(router.push).toHaveBeenCalledWith({
        pathname: '/einladen/[eventId]',
        params: {eventId: 'e2'},
      }),
    );
  });

  it('allows account actions directly once signed in', async () => {
    mockMeApi();
    await renderProbe();
    await fireEvent.press(screen.getByTestId('login'));
    await waitFor(() =>
      expect(screen.getByTestId('status')).toHaveTextContent('signedIn'),
    );
    await fireEvent.press(screen.getByTestId('heart'));
    expect(allowed).toBe(true);
    expect(screen.queryByText('Lieblingsfeste merken')).toBeNull();
  });

  it('stays silent when the user cancels in the browser', async () => {
    mockMeApi();
    await renderProbe(fakeGateway({type: 'cancel'}));
    await fireEvent.press(screen.getByTestId('login'));
    expect(screen.getByTestId('status')).toHaveTextContent('guest');
    expect(screen.queryByText(/fehlgeschlagen/)).toBeNull();
  });

  it('shows a toast when the login fails', async () => {
    mockMeApi();
    await renderProbe(fakeGateway({type: 'error'}));
    await fireEvent.press(screen.getByTestId('login'));
    expect(
      await screen.findByText(
        'Anmeldung fehlgeschlagen · Bitte erneut versuchen',
      ),
    ).toBeOnTheScreen();
    expect(screen.getByTestId('status')).toHaveTextContent('guest');
  });
});

describe('AuthProvider session', () => {
  it('restores a stored session on app start', async () => {
    await secureTokenStore.save(testTokens('stored'));
    const calls = mockMeApi();
    await renderProbe();
    expect(screen.getByTestId('status')).toHaveTextContent('signedIn');
    await waitFor(() =>
      expect(screen.getByTestId('user')).toHaveTextContent('Lena'),
    );
    expect(calls[0]?.authorization).toBe('Bearer stored');
  });

  it('falls back to guest mode when the renewal is rejected', async () => {
    await secureTokenStore.save(testTokens('old', -1000));
    rejectRefresh();
    mockMeApi({status: 401});
    await renderProbe();

    expect(
      await screen.findByText('Bitte melde dich erneut an'),
    ).toBeOnTheScreen();
    await waitFor(() =>
      expect(screen.getByTestId('status')).toHaveTextContent('guest'),
    );
    expect(await secureTokenStore.load()).toBeNull();
  });

  it('logs out: revokes the refresh token and deletes local tokens', async () => {
    mockMeApi();
    const gateway = fakeGateway();
    await renderProbe(gateway);
    await fireEvent.press(screen.getByTestId('login'));
    await waitFor(() =>
      expect(screen.getByTestId('status')).toHaveTextContent('signedIn'),
    );

    await fireEvent.press(screen.getByTestId('logout'));

    expect(await screen.findByText('Du bist abgemeldet')).toBeOnTheScreen();
    expect(gateway.revoke).toHaveBeenCalledWith('rt-at-1');
    expect(screen.getByTestId('status')).toHaveTextContent('guest');
    expect(authSession.current).toBeNull();
    expect(await secureTokenStore.load()).toBeNull();
  });
});
