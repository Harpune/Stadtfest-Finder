import {act, fireEvent, screen, waitFor} from '@testing-library/react-native';
import React from 'react';
import {Alert} from 'react-native';

import {useAuth} from '@/features/auth/AuthProvider';
import {authSession} from '@/features/auth/authSession';
import {
  AuthTestProviders,
  fakeGateway,
  mockMeApi,
  resetAuth,
  testTokens,
} from '@/features/auth/testing';
import {secureTokenStore} from '@/features/auth/tokens';
import {renderWithProviders} from '@/test-utils';

import {AccountScreen} from './AccountScreen';

function WhenLoaded() {
  const {user} = useAuth();
  return user ? <AccountScreen /> : null;
}

async function renderAccount() {
  await authSession.start(testTokens());
  await renderWithProviders(
    <AuthTestProviders gateway={fakeGateway()}>
      <WhenLoaded />
    </AuthTestProviders>,
  );
  await screen.findByTestId('account.firstName');
}

async function confirmDeletion() {
  const [, , buttons] = jest.mocked(Alert.alert).mock.calls[0] ?? [];
  const confirm = buttons?.find(b => b.style === 'destructive');
  await act(async () => {
    await confirm?.onPress?.();
  });
}

beforeEach(async () => {
  await resetAuth();
  jest.clearAllMocks();
  jest.spyOn(Alert, 'alert').mockImplementation(() => undefined);
});

describe('AccountScreen', () => {
  it('shows email and names and saves changes', async () => {
    const calls = mockMeApi();
    await renderAccount();
    expect(screen.getByTestId('account.email')).toHaveTextContent(
      'lena@example.test',
    );
    expect(screen.getByTestId('account.firstName')).toHaveProp('value', 'Lena');

    await fireEvent.changeText(
      screen.getByTestId('account.lastName'),
      'Muster',
    );
    await fireEvent.press(screen.getByTestId('account.save'));

    expect(await screen.findByText('Name gespeichert')).toBeOnTheScreen();
    expect(calls.at(-1)).toMatchObject({method: 'PATCH', path: '/v1/me'});
  });

  it('does not save an empty name', async () => {
    const calls = mockMeApi();
    await renderAccount();
    await fireEvent.changeText(screen.getByTestId('account.firstName'), '   ');
    await fireEvent.press(screen.getByTestId('account.save'));
    expect(screen.getByTestId('account.firstName.error')).toBeOnTheScreen();
    expect(calls.some(call => call.method === 'PATCH')).toBe(false);
  });

  it('deletes the account after confirmation and signs out', async () => {
    const calls = mockMeApi();
    await renderAccount();

    await fireEvent.press(screen.getByTestId('account.delete'));
    expect(Alert.alert).toHaveBeenCalledWith(
      'Konto endgültig löschen?',
      expect.stringContaining('lässt sich nicht rückgängig machen'),
      expect.any(Array),
    );
    await confirmDeletion();

    expect(
      await screen.findByText('Dein Konto wurde gelöscht'),
    ).toBeOnTheScreen();
    expect(calls).toContainEqual(
      expect.objectContaining({method: 'DELETE', path: '/v1/me'}),
    );
    await waitFor(async () => expect(await secureTokenStore.load()).toBeNull());
  });

  it('keeps the session if the deletion fails', async () => {
    mockMeApi();
    await renderAccount();
    mockMeApi({status: 503});
    await fireEvent.press(screen.getByTestId('account.delete'));
    await confirmDeletion();
    expect(
      await screen.findByText(
        'Löschen fehlgeschlagen · Bitte erneut versuchen',
      ),
    ).toBeOnTheScreen();
    expect(authSession.current).not.toBeNull();
  });
});
