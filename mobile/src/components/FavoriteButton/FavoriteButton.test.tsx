import {fireEvent, screen} from '@testing-library/react-native';
import React from 'react';

import {renderWithProviders} from '@/test-utils';

import {FavoriteButton} from './FavoriteButton';

describe('FavoriteButton', () => {
  it('exposes the favorite state and reports presses', async () => {
    const onPress = jest.fn();
    await renderWithProviders(
      <FavoriteButton
        active
        accessibilityLabel="Oktoberfest merken"
        onPress={onPress}
        testID="fav"
      />,
    );
    expect(screen.getByTestId('fav')).toBeSelected();
    await fireEvent.press(screen.getByTestId('fav'));
    expect(onPress).toHaveBeenCalled();
  });
});
