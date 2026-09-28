import {act, fireEvent, screen} from '@testing-library/react-native';
import React from 'react';

import {renderWithProviders} from '@/test-utils';

import {Button} from '../Button/Button';
import {useToast} from './Toast';

function Trigger({withAction = false}: {withAction?: boolean}) {
  const toast = useToast();
  const retry = jest.fn();
  return (
    <Button
      label="Zeigen"
      testID="trigger"
      onPress={() =>
        toast(
          'Feste konnten nicht geladen werden',
          withAction
            ? {action: {label: 'Erneut versuchen', onPress: retry}}
            : undefined,
        )
      }
    />
  );
}

describe('Toast', () => {
  beforeEach(() => jest.useFakeTimers());
  afterEach(() => jest.useRealTimers());

  it('shows a message and hides it after ~2.2 s', async () => {
    await renderWithProviders(<Trigger />);
    await fireEvent.press(screen.getByTestId('trigger'));
    expect(
      screen.getByText('Feste konnten nicht geladen werden'),
    ).toBeOnTheScreen();

    await act(() => jest.advanceTimersByTime(250 + 2200 + 250 + 50));
    expect(screen.queryByTestId('toast')).toBeNull();
  });

  it('renders an optional action', async () => {
    await renderWithProviders(<Trigger withAction />);
    await fireEvent.press(screen.getByTestId('trigger'));
    expect(screen.getByTestId('toast.action')).toBeOnTheScreen();
  });
});
