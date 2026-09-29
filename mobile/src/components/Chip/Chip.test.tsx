import {fireEvent, screen} from '@testing-library/react-native';
import React from 'react';

import {themes} from '@/theme';
import {renderWithProviders} from '@/test-utils';

import {Chip} from './Chip';

describe('Chip', () => {
  it('shows emoji, label and count and reports selection', async () => {
    const onPress = jest.fn();
    await renderWithProviders(
      <Chip
        label="Stadtfest"
        emoji="🎪"
        count={3}
        active
        onPress={onPress}
        testID="chip"
      />,
    );
    expect(screen.getByText('Stadtfest')).toBeOnTheScreen();
    expect(screen.getByText('3')).toBeOnTheScreen();
    expect(screen.getByTestId('chip')).toBeSelected();
    await fireEvent.press(screen.getByTestId('chip'));
    expect(onPress).toHaveBeenCalledTimes(1);
  });

  it('uses #15111C text on amber when active in both schemes', async () => {
    for (const scheme of ['dark', 'light'] as const) {
      const {unmount} = await renderWithProviders(
        <Chip label="Heute" active onPress={jest.fn()} testID="chip" />,
        {scheme},
      );
      expect(screen.getByText('Heute')).toHaveStyle({
        color: themes[scheme].colors.onPrimary,
      });
      await unmount();
    }
  });
});
