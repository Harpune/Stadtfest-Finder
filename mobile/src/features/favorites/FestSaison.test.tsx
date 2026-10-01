import {fireEvent, screen} from '@testing-library/react-native';
import React from 'react';

import {renderWithProviders} from '@/test-utils';

import {FestSaison, FestSaisonProps} from './FestSaison';
import type {FavoriteEntry} from './timeline';

function entry(
  id: string,
  name: string,
  startDate: string,
  endDate: string,
  status: FavoriteEntry['status'] = 'published',
): FavoriteEntry {
  return {
    id,
    name,
    shortName: name,
    status,
    startDate,
    endDate,
    place: 'Marktplatz',
    city: 'Aalen',
    lat: 48.8,
    lon: 10.1,
    categoryId: 'c1',
    categoryName: 'Stadtfest',
    emoji: '🎪',
    favoritedAt: '2026-09-01T10:00:00Z',
  };
}

const FAVORITES = [
  entry('past', 'Ipfmesse', '2026-07-01', '2026-07-05'),
  entry('running', 'Oktoberfest', '2026-09-19', '2026-10-04'),
  entry('later', 'Stadtfest Gmünd', '2026-10-10', '2026-10-11'),
  entry('off', 'Weinfest', '2026-10-20', '2026-10-21', 'cancelled'),
];

function renderSaison(props: Partial<FestSaisonProps> = {}) {
  return renderWithProviders(
    <FestSaison
      favorites={FAVORITES}
      loading={false}
      error={false}
      today="2026-09-25"
      onOpen={jest.fn()}
      onDiscover={jest.fn()}
      onRetry={jest.fn()}
      {...props}
    />,
  );
}

describe('FestSaison', () => {
  it('groups upcoming favorites by month and highlights the running one', async () => {
    await renderSaison();
    expect(screen.getByText('3 Favoriten stehen an')).toBeOnTheScreen();
    expect(screen.getByText('September 2026')).toBeOnTheScreen();
    expect(screen.getByText('Oktober 2026')).toBeOnTheScreen();
    expect(screen.getByText('● Läuft · noch 9 Tage')).toBeOnTheScreen();
    expect(screen.getByText('20.–21. Okt · Abgesagt')).toBeOnTheScreen();
    // Past favorites stay hidden until requested.
    expect(screen.queryByText('Ipfmesse')).toBeNull();
  });

  it('shows past favorites above the today marker on request', async () => {
    await renderSaison();
    await fireEvent.press(screen.getByText('↑ Vergangene einblenden (1)'));

    expect(screen.getByText('Ipfmesse')).toBeOnTheScreen();
    expect(screen.getByText('1.–5. Jul · vorbei')).toBeOnTheScreen();
    expect(screen.getByText('HEUTE · FR 25.09.')).toBeOnTheScreen();

    await fireEvent.press(screen.getByText('↓ Vergangene ausblenden'));
    expect(screen.queryByText('Ipfmesse')).toBeNull();
  });

  it('opens the detail of a tapped entry', async () => {
    const onOpen = jest.fn();
    await renderSaison({onOpen});
    await fireEvent.press(screen.getByTestId('favorites.entry.later'));
    expect(onOpen).toHaveBeenCalledWith('later');
  });

  it('shows the empty state with "Feste entdecken"', async () => {
    const onDiscover = jest.fn();
    await renderSaison({favorites: [], onDiscover});
    expect(screen.getByText('Noch keine Favoriten')).toBeOnTheScreen();
    await fireEvent.press(screen.getByTestId('favorites.discover'));
    expect(onDiscover).toHaveBeenCalled();
  });

  it('offers a retry when loading failed', async () => {
    const onRetry = jest.fn();
    await renderSaison({favorites: undefined, error: true, onRetry});
    await fireEvent.press(screen.getByTestId('favorites.retry'));
    expect(onRetry).toHaveBeenCalled();
  });
});
