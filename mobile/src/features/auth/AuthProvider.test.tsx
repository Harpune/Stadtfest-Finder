import {fireEvent, screen, waitFor} from '@testing-library/react-native';
import React from 'react';
import {Pressable, Text} from 'react-native';

import {renderWithProviders} from '@/test-utils';

import {AuthProvider, useAuth} from './AuthProvider';

function Probe() {
  const {pendingAction, requestAccountAction} = useAuth();
  return (
    <>
      <Pressable
        testID="heart"
        onPress={() => requestAccountAction({type: 'favorite', eventId: 'e1'})}
      />
      <Pressable
        testID="invite"
        onPress={() => requestAccountAction({type: 'invite', eventId: 'e2'})}
      />
      <Text testID="pending">
        {pendingAction ? JSON.stringify(pendingAction) : 'none'}
      </Text>
    </>
  );
}

async function renderProbe() {
  await renderWithProviders(
    <AuthProvider>
      <Probe />
    </AuthProvider>,
  );
}

describe('AuthProvider guest hint', () => {
  it('remembers the action and shows the matching hint', async () => {
    await renderProbe();
    await fireEvent.press(screen.getByTestId('heart'));
    expect(screen.getByText('Lieblingsfeste merken')).toBeOnTheScreen();
    expect(screen.getByTestId('pending')).toHaveTextContent(
      JSON.stringify({type: 'favorite', eventId: 'e1'}),
    );
  });

  it('discards the pending action with "Weiter ohne Konto"', async () => {
    await renderProbe();
    await fireEvent.press(screen.getByTestId('invite'));
    expect(screen.getByText('Freunde einladen')).toBeOnTheScreen();
    await fireEvent.press(screen.getByTestId('guestHint.dismiss'));
    expect(screen.getByTestId('pending')).toHaveTextContent('none');
    await waitFor(() =>
      expect(screen.queryByText('Freunde einladen')).toBeNull(),
    );
  });

  it('keeps the pending action for the login (R05 placeholder)', async () => {
    await renderProbe();
    await fireEvent.press(screen.getByTestId('heart'));
    await fireEvent.press(screen.getByTestId('guestHint.login'));
    expect(screen.getByText('Anmeldung folgt in Kürze.')).toBeOnTheScreen();
    expect(screen.getByTestId('pending')).not.toHaveTextContent('none');
  });
});
