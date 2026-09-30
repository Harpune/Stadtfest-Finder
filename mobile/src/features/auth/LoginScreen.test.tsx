import {act, fireEvent, screen, waitFor} from '@testing-library/react-native';
import {router} from 'expo-router';
import React from 'react';

import {renderWithProviders} from '@/test-utils';

import type {LoginResult} from './oidc';
import {LoginScreen} from './LoginScreen';
import {AuthTestProviders, fakeGateway, mockMeApi, resetAuth} from './testing';

describe('LoginScreen', () => {
  beforeEach(() => jest.mocked(router.back).mockClear());
  afterEach(async () => {
    jest.restoreAllMocks();
    await resetAuth();
  });

  it('aborts a pending login when the screen is closed', async () => {
    mockMeApi();
    const gateway = fakeGateway();
    let isAborted: (() => boolean) | undefined;
    let finish: (result: LoginResult) => void = () => undefined;
    gateway.login.mockImplementation((_method, aborted) => {
      isAborted = aborted;
      return new Promise<LoginResult>(resolve => {
        finish = resolve;
      });
    });
    const view = await renderWithProviders(
      <AuthTestProviders gateway={gateway}>
        <LoginScreen />
      </AuthTestProviders>,
    );

    // Not awaited: the press handler stays pending until the login resolves.
    void fireEvent.press(screen.getByTestId('login.email'));
    await waitFor(() => expect(isAborted).toBeDefined());
    expect(isAborted?.()).toBe(false);

    await view.unmount();
    expect(isAborted?.()).toBe(true);

    // The late result must not pop whatever screen is open by now.
    await act(async () => finish({type: 'cancel'}));
    expect(router.back).not.toHaveBeenCalled();
  });
});
