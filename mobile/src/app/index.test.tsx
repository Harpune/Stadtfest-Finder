import {fireEvent, screen} from '@testing-library/react-native';
import React from 'react';

import {renderWithProviders} from '@/test-utils';

import StartScreen from './index';

describe('StartScreen', () => {
  it('shows the app name and a discover action', async () => {
    await renderWithProviders(<StartScreen />);
    expect(screen.getByTestId('start.title')).toHaveTextContent(
      'Stadtfest-Finder',
    );
    await fireEvent.press(screen.getByTestId('start.discover'));
    expect(screen.getByText('Die Karte folgt in Kürze.')).toBeOnTheScreen();
  });
});
