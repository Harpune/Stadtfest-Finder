import {fireEvent, screen} from '@testing-library/react-native';
import React from 'react';

import {renderWithProviders} from '@/test-utils';

import {UNKNOWN_CATEGORY} from './categoryLookup';
import {EventList, EventListProps} from './EventList';
import type {EventSummary} from './useDiscoverData';

const EVENT: EventSummary = {
  id: 'e1',
  name: 'Reichsstädter Tage',
  shortName: 'Reichsstädter',
  status: 'published',
  startDate: '2026-09-22',
  endDate: '2026-10-03',
  place: 'Marktplatz',
  city: 'Aalen',
  lat: 48.84,
  lon: 10.09,
  categoryId: 'c1',
  distanceKm: 1.4,
};

function renderList(props: Partial<EventListProps> = {}) {
  return renderWithProviders(
    <EventList
      items={[EVENT]}
      total={1}
      areaName="Aalen"
      onChangeArea={jest.fn()}
      today="2026-09-25"
      categoryOf={() => ({name: 'Stadtfest', emoji: '🎪', color: '#FFB547'})}
      loading={false}
      refreshing={false}
      loadingMore={false}
      topInset={0}
      bottomInset={0}
      onRefresh={jest.fn()}
      onEndReached={jest.fn()}
      onOpen={jest.fn()}
      onFavorite={jest.fn()}
      {...props}
    />,
  );
}

describe('EventList', () => {
  it('shows header, status, name and pills', async () => {
    const onOpen = jest.fn();
    await renderList({onOpen});
    expect(screen.getByText('1 Fest im Kartenausschnitt')).toBeOnTheScreen();
    expect(screen.getByText('um Aalen')).toBeOnTheScreen();
    expect(screen.getByText('Läuft gerade')).toBeOnTheScreen();
    expect(screen.getByText('Läuft · noch 8 Tage')).toBeOnTheScreen();
    expect(screen.getByText('🎪 Stadtfest')).toBeOnTheScreen();
    expect(screen.getByText('1,4 km')).toBeOnTheScreen();
    await fireEvent.press(screen.getByTestId('discover.list.card.e1'));
    expect(onOpen).toHaveBeenCalledWith(EVENT);
  });

  it('shows skeletons while loading the first page', async () => {
    await renderList({items: [], loading: true});
    expect(screen.queryByText('Reichsstädter Tage')).toBeNull();
    expect(screen.queryByTestId('discover.empty.area')).toBeNull();
  });

  it('shows the empty state with its actions', async () => {
    const expand = jest.fn();
    await renderList({
      items: [],
      total: 0,
      empty: {
        testID: 'discover.empty.area',
        title: 'Keine Feste in diesem Kartenausschnitt',
        text: 'Zoome heraus …',
        primary: {
          label: 'Herauszoomen',
          onPress: expand,
          testID: 'discover.empty.zoomOut',
        },
      },
    });
    expect(
      screen.getByText('Keine Feste in diesem Kartenausschnitt'),
    ).toBeOnTheScreen();
    await fireEvent.press(screen.getByTestId('discover.empty.zoomOut'));
    expect(expand).toHaveBeenCalled();
  });

  it('falls back to a neutral category for inactive categories', async () => {
    await renderList({categoryOf: () => UNKNOWN_CATEGORY});
    expect(screen.getByText('📍 Fest')).toBeOnTheScreen();
  });
});
