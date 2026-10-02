import {QueryClient, QueryClientProvider} from '@tanstack/react-query';
import {act, renderHook} from '@testing-library/react-native';
import {router} from 'expo-router';
import React, {PropsWithChildren} from 'react';
import {SafeAreaProvider} from 'react-native-safe-area-context';

import {ToastProvider} from '@/components';
import {ThemeProvider} from '@/theme';

import {useExitModeration} from './useModeration';

describe('useExitModeration', () => {
  it('leaves the whole moderation stack, also from the form ("Beenden", 08-01)', async () => {
    const client = new QueryClient();
    function Wrapper({children}: PropsWithChildren) {
      return (
        <SafeAreaProvider
          initialMetrics={{
            frame: {x: 0, y: 0, width: 390, height: 844},
            insets: {top: 0, left: 0, right: 0, bottom: 0},
          }}
        >
          <QueryClientProvider client={client}>
            <ThemeProvider>
              <ToastProvider>{children}</ToastProvider>
            </ThemeProvider>
          </QueryClientProvider>
        </SafeAreaProvider>
      );
    }
    const {result} = await renderHook(() => useExitModeration(), {
      wrapper: Wrapper,
    });

    await act(async () => result.current());

    // dismissAll() would only pop the nested moderation stack back to its overview.
    expect(router.dismissTo).toHaveBeenCalledWith('/');
    expect(router.dismissAll).not.toHaveBeenCalled();
  });
});
