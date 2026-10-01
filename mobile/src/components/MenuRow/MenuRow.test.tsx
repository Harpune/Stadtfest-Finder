import {fireEvent, screen} from '@testing-library/react-native';
import React from 'react';

import {renderWithProviders} from '@/test-utils';

import {MenuRow} from './MenuRow';

describe('MenuRow', () => {
  it('toggles the switch when the row is pressed', async () => {
    const onSwitchChange = jest.fn();
    await renderWithProviders(
      <MenuRow
        label="Dunkelmodus"
        switchValue
        onSwitchChange={onSwitchChange}
        testID="row"
      />,
    );
    expect(screen.getByTestId('row')).toBeChecked();
    await fireEvent.press(screen.getByTestId('row'));
    expect(onSwitchChange).toHaveBeenCalledWith(false);
  });

  it('runs the action of a plain row', async () => {
    const onPress = jest.fn();
    await renderWithProviders(
      <MenuRow
        label="Abmelden"
        tone="secondary"
        onPress={onPress}
        testID="row"
      />,
    );
    await fireEvent.press(screen.getByText('Abmelden'));
    expect(onPress).toHaveBeenCalled();
  });
});
