import {screen} from '@testing-library/react-native';
import React from 'react';

import {themes} from '@/theme';
import {renderWithProviders} from '@/test-utils';

import {Text} from './Text';

describe('Text', () => {
  it.each(['dark', 'light'] as const)(
    'uses theme colors in %s mode',
    async scheme => {
      await renderWithProviders(<Text>Hallo</Text>, {scheme});
      expect(screen.getByText('Hallo')).toHaveStyle({
        color: themes[scheme].colors.onSurface,
      });
    },
  );

  it('renders section labels muted and uppercase', async () => {
    await renderWithProviders(<Text variant="label">Zeitraum</Text>);
    expect(screen.getByText('Zeitraum')).toHaveStyle({
      textTransform: 'uppercase',
      color: themes.dark.colors.onSurfaceMuted,
    });
  });
});
