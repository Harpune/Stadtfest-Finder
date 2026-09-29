import {fireEvent, screen} from '@testing-library/react-native';
import React from 'react';

import {
  DEFAULT_FILTER,
  DiscoverFilter,
  monthOptions,
} from '@/features/discover/filter';
import {renderWithProviders} from '@/test-utils';

import {FilterSheet, FilterSheetProps} from './FilterSheet';

const CATEGORIES = [
  {id: 'c1', name: 'Stadtfest', emoji: '🎪'},
  {id: 'c2', name: 'Weihnachtsmarkt', emoji: '🎄'},
];

async function renderSheet(props: Partial<FilterSheetProps> = {}) {
  const handlers = {
    onApply: jest.fn(),
    onClose: jest.fn(),
    onDraftChange: jest.fn(),
  };
  const result = await renderWithProviders(
    <FilterSheet
      visible
      filter={DEFAULT_FILTER}
      categories={CATEGORIES}
      monthOptions={monthOptions('2026-10-01')}
      originCaption="vom Standort Aalen"
      previewCount={8}
      {...handlers}
      {...props}
    />,
  );
  return {...handlers, result};
}

describe('FilterSheet', () => {
  it('edits a draft and applies it on confirm', async () => {
    const {onApply, onDraftChange} = await renderSheet();
    await fireEvent.press(screen.getByTestId('filter.time.today'));
    await fireEvent.press(screen.getByTestId('filter.category.c2'));

    const expected: DiscoverFilter = {
      ...DEFAULT_FILTER,
      time: 'today',
      categoryIds: ['c2'],
    };
    expect(onDraftChange).toHaveBeenLastCalledWith(expected);
    expect(onApply).not.toHaveBeenCalled();

    await fireEvent.press(screen.getByTestId('filter.apply'));
    expect(onApply).toHaveBeenCalledWith(expected);
  });

  it('shows the month grid for "Zeitraum wählen" with multi-select', async () => {
    const {onApply} = await renderSheet();
    expect(screen.queryByTestId('filter.months')).toBeNull();
    await fireEvent.press(screen.getByTestId('filter.time.months'));
    await fireEvent.press(screen.getByTestId('filter.months.2026-11'));
    await fireEvent.press(screen.getByTestId('filter.months.2026-12'));
    await fireEvent.press(screen.getByTestId('filter.apply'));
    expect(onApply).toHaveBeenCalledWith({
      ...DEFAULT_FILTER,
      time: 'months',
      months: ['2026-11', '2026-12'],
    });
  });

  it('resets only the draft', async () => {
    const applied = {...DEFAULT_FILTER, time: 'weekend' as const, radiusKm: 50};
    const {onApply} = await renderSheet({filter: applied});
    expect(screen.getByTestId('filter.time.weekend')).toBeSelected();
    await fireEvent.press(screen.getByTestId('filter.reset'));
    expect(screen.getByTestId('filter.time.all')).toBeSelected();
    expect(screen.getByText('bis 150 km')).toBeOnTheScreen();
    expect(onApply).not.toHaveBeenCalled();
  });

  it('labels the button with the live count, and for zero results', async () => {
    const first = await renderSheet({previewCount: 1});
    expect(screen.getByText('1 Fest anzeigen')).toBeOnTheScreen();
    await first.result.unmount();
    await renderSheet({previewCount: 0});
    expect(
      screen.getByText('Keine Treffer – trotzdem anwenden'),
    ).toBeOnTheScreen();
  });

  it('closes without applying', async () => {
    const {onClose, onApply} = await renderSheet();
    await fireEvent.press(screen.getByTestId('filter.sheet.close'));
    expect(onClose).toHaveBeenCalled();
    expect(onApply).not.toHaveBeenCalled();
  });
});
