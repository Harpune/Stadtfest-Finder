/** Test helpers: render components inside the app providers. */
import {render, RenderOptions} from '@testing-library/react-native';
import React, {PropsWithChildren, ReactElement} from 'react';
import {SafeAreaProvider} from 'react-native-safe-area-context';

import {ToastProvider} from '@/components/Toast/Toast';
import {ColorScheme, ThemeProvider} from '@/theme';

const METRICS = {
  frame: {x: 0, y: 0, width: 390, height: 844},
  insets: {top: 44, left: 0, right: 0, bottom: 30},
};

export async function renderWithProviders(
  ui: ReactElement,
  {scheme = 'dark', ...options}: RenderOptions & {scheme?: ColorScheme} = {},
) {
  function Wrapper({children}: PropsWithChildren) {
    return (
      <SafeAreaProvider initialMetrics={METRICS}>
        <ThemeProvider forcedScheme={scheme}>
          <ToastProvider>{children}</ToastProvider>
        </ThemeProvider>
      </SafeAreaProvider>
    );
  }
  return render(ui, {wrapper: Wrapper, ...options});
}
