import {fireEvent, screen} from '@testing-library/react-native';
import React from 'react';

import {renderWithProviders} from '@/test-utils';

import {Text} from '../Text/Text';
import {Accordion} from './Accordion';

describe('Accordion', () => {
  it('shows the content only when expanded and reports taps', async () => {
    const onToggle = jest.fn();
    const {rerender} = await renderWithProviders(
      <Accordion
        title="Weitere Filter"
        summary="2 Filter aktiv"
        expanded={false}
        onToggle={onToggle}
        testID="acc"
      >
        <Text>Inhalt</Text>
      </Accordion>,
    );
    expect(screen.getByText('2 Filter aktiv')).toBeOnTheScreen();
    expect(screen.queryByText('Inhalt')).toBeNull();
    expect(screen.getByTestId('acc')).toBeCollapsed();
    await fireEvent.press(screen.getByTestId('acc'));
    expect(onToggle).toHaveBeenCalledTimes(1);

    await rerender(
      <Accordion
        title="Weitere Filter"
        expanded
        onToggle={onToggle}
        testID="acc"
      >
        <Text>Inhalt</Text>
      </Accordion>,
    );
    expect(screen.getByText('Inhalt')).toBeOnTheScreen();
    expect(screen.getByTestId('acc')).toBeExpanded();
  });

  it('ignores taps when disabled', async () => {
    const onToggle = jest.fn();
    await renderWithProviders(
      <Accordion
        title="Weitere Filter"
        expanded={false}
        onToggle={onToggle}
        disabled
        testID="acc"
      />,
    );
    await fireEvent.press(screen.getByTestId('acc'));
    expect(onToggle).not.toHaveBeenCalled();
  });
});
