import {fireEvent, screen} from '@testing-library/react-native';
import React from 'react';

import {themes} from '@/theme';
import {renderWithProviders} from '@/test-utils';

import {Button} from './Button';

describe('Button', () => {
  it('calls onPress', async () => {
    const onPress = jest.fn();
    await renderWithProviders(
      <Button label="Anwenden" onPress={onPress} testID="btn" />,
    );
    await fireEvent.press(screen.getByTestId('btn'));
    expect(onPress).toHaveBeenCalledTimes(1);
  });

  it('does not fire when disabled', async () => {
    const onPress = jest.fn();
    await renderWithProviders(
      <Button label="Anwenden" onPress={onPress} testID="btn" disabled />,
    );
    await fireEvent.press(screen.getByTestId('btn'));
    expect(onPress).not.toHaveBeenCalled();
    expect(screen.getByTestId('btn')).toBeDisabled();
  });

  it('shows the loading label and blocks presses while loading', async () => {
    const onPress = jest.fn();
    await renderWithProviders(
      <Button label="Anmelden" onPress={onPress} testID="btn" loading />,
    );
    expect(screen.getByText('Einen Moment …')).toBeOnTheScreen();
    await fireEvent.press(screen.getByTestId('btn'));
    expect(onPress).not.toHaveBeenCalled();
  });

  it('uses dark text on amber in both schemes (contrast rule)', async () => {
    for (const scheme of ['dark', 'light'] as const) {
      const {unmount} = await renderWithProviders(
        <Button label="Los" onPress={jest.fn()} testID="btn" />,
        {scheme},
      );
      expect(screen.getByText('Los')).toHaveStyle({
        color: themes[scheme].colors.onPrimary,
      });
      expect(themes[scheme].colors.onPrimary).toBe('#15111C');
      await unmount();
    }
  });
});
