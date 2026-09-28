import type {Preview} from '@storybook/react-native';
import React from 'react';
import {View} from 'react-native';

import {ToastProvider} from '@/components/Toast/Toast';
import {ThemeProvider, useTheme} from '@/theme';

function Canvas({children}: {children: React.ReactNode}) {
  const theme = useTheme();
  return (
    <View
      style={{flex: 1, padding: 16, backgroundColor: theme.colors.background}}
    >
      {children}
    </View>
  );
}

const preview: Preview = {
  decorators: [
    (Story, {globals}) => (
      <ThemeProvider
        forcedScheme={globals.scheme === 'light' ? 'light' : 'dark'}
      >
        <ToastProvider>
          <Canvas>
            <Story />
          </Canvas>
        </ToastProvider>
      </ThemeProvider>
    ),
  ],
  globalTypes: {
    scheme: {
      description: 'Dunkel- oder Hellmodus',
      defaultValue: 'dark',
      toolbar: {items: ['dark', 'light']},
    },
  },
};

export default preview;
