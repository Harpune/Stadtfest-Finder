import {fireEvent, screen, waitFor} from '@testing-library/react-native';
import {router} from 'expo-router';
import React from 'react';

import {useAuth} from '@/features/auth/AuthProvider';
import {authSession} from '@/features/auth/authSession';
import {
  AuthTestProviders,
  fakeGateway,
  LENA,
  mockMeApi,
  resetAuth,
  testTokens,
} from '@/features/auth/testing';
import {renderWithProviders} from '@/test-utils';

import {ProfileDrawer} from './ProfileDrawer';

function StatusProbe() {
  const {status} = useAuth();
  return (
    <>
      {status === 'restoring' ? null : (
        <ProfileDrawer visible onClose={onClose} />
      )}
    </>
  );
}

const onClose = jest.fn();

async function renderDrawer() {
  await renderWithProviders(
    <AuthTestProviders gateway={fakeGateway()}>
      <StatusProbe />
    </AuthTestProviders>,
  );
  await screen.findByTestId('drawer');
}

beforeEach(async () => {
  await resetAuth();
  jest.clearAllMocks();
});

describe('ProfileDrawer', () => {
  it('shows the guest variant with login', async () => {
    mockMeApi();
    await renderDrawer();
    expect(
      screen.getByText('Deine Festsaison auf einen Blick'),
    ).toBeOnTheScreen();
    expect(
      screen.getByText('Alle Feste kannst du auch ohne Konto entdecken.'),
    ).toBeOnTheScreen();
    await fireEvent.press(screen.getByTestId('drawer.login'));
    expect(onClose).toHaveBeenCalled();
    expect(router.push).toHaveBeenCalledWith('/login');
  });

  it('shows name and email when signed in and opens the account page', async () => {
    await authSession.start(testTokens());
    mockMeApi();
    await renderDrawer();
    await waitFor(() =>
      expect(screen.getByTestId('drawer.name')).toHaveTextContent(
        'Lena Beispiel',
      ),
    );
    expect(screen.getByText('lena@example.test')).toBeOnTheScreen();
    await fireEvent.press(screen.getByTestId('drawer.user'));
    expect(router.push).toHaveBeenCalledWith('/konto');
  });

  it('logs out from the footer', async () => {
    await authSession.start(testTokens());
    mockMeApi();
    await renderDrawer();
    await fireEvent.press(await screen.findByTestId('drawer.logout'));
    expect(await screen.findByText('Du bist abgemeldet')).toBeOnTheScreen();
  });

  it('asks for the name if the IdP did not provide one', async () => {
    await authSession.start(testTokens());
    const calls = mockMeApi({me: {...LENA, firstName: '', lastName: ''}});
    await renderDrawer();

    expect(await screen.findByText('Wie heißt du?')).toBeOnTheScreen();
    await fireEvent.press(screen.getByTestId('nameSheet.save'));
    expect(screen.getAllByText('Bitte gib 1 bis 50 Zeichen ein.')).toHaveLength(
      2,
    );

    await fireEvent.changeText(
      screen.getByTestId('nameSheet.firstName'),
      ' Mia ',
    );
    await fireEvent.changeText(
      screen.getByTestId('nameSheet.lastName'),
      'Muster',
    );
    await fireEvent.press(screen.getByTestId('nameSheet.save'));

    expect(await screen.findByText('Name gespeichert')).toBeOnTheScreen();
    expect(calls).toContainEqual(
      expect.objectContaining({
        method: 'PATCH',
        path: '/v1/me',
        body: JSON.stringify({firstName: 'Mia', lastName: 'Muster'}),
      }),
    );
  });
});
