import {QueryClient, QueryClientProvider} from '@tanstack/react-query';
import {act, fireEvent, screen, waitFor} from '@testing-library/react-native';
import React from 'react';
import {Pressable, Text} from 'react-native';

import {AuthProvider} from '@/features/auth/AuthProvider';
import {renderWithProviders} from '@/test-utils';

import type {FavoriteEntry} from './timeline';
import {
  FAVORITES_QUERY,
  useFavoriteIds,
  useToggleFavorite,
} from './useFavorites';

const EVENT: FavoriteEntry = {
  id: 'e1',
  name: 'Oktoberfest',
  shortName: 'Oktoberfest',
  status: 'published',
  startDate: '2026-09-19',
  endDate: '2026-10-04',
  place: 'Theresienwiese',
  city: 'München',
  lat: 48.13,
  lon: 11.55,
  categoryId: 'c1',
  categoryName: 'Volksfest',
  emoji: '🎡',
  favoritedAt: '2026-09-01T10:00:00Z',
};

function Probe() {
  const ids = useFavoriteIds();
  const toggle = useToggleFavorite();
  return (
    <>
      <Text testID="state">{ids.has('e1') ? 'favorite' : 'none'}</Text>
      <Pressable testID="add" onPress={() => void toggle(EVENT, true)} />
      <Pressable testID="remove" onPress={() => void toggle(EVENT, false)} />
    </>
  );
}

function mockFavoritesApi(writeStatus: number) {
  let release: () => void = () => undefined;
  const gate = new Promise<void>(resolve => {
    release = resolve;
  });
  jest.spyOn(global, 'fetch').mockImplementation(async input => {
    const request = input as Request;
    if (request.method === 'GET') {
      return new Response(JSON.stringify({items: []}), {
        status: 200,
        headers: {'Content-Type': 'application/json'},
      });
    }
    await gate; // keep the write pending to observe the optimistic state
    return new Response(null, {status: writeStatus});
  });
  return () => release();
}

async function renderProbe(client: QueryClient) {
  client.setQueryData(FAVORITES_QUERY.queryKey, {items: []});
  await renderWithProviders(
    <QueryClientProvider client={client}>
      <AuthProvider>
        <Probe />
      </AuthProvider>
    </QueryClientProvider>,
  );
}

describe('useToggleFavorite', () => {
  afterEach(() => jest.restoreAllMocks());

  it('fills the heart at once and confirms with a toast', async () => {
    const client = new QueryClient({defaultOptions: {queries: {retry: false}}});
    const finish = mockFavoritesApi(204);
    await renderProbe(client);

    await fireEvent.press(screen.getByTestId('add'));
    await waitFor(() =>
      expect(client.getQueryData(FAVORITES_QUERY.queryKey)).toEqual({
        items: [EVENT],
      }),
    );
    await act(async () => finish());

    expect(
      await screen.findByText('Zu Favoriten hinzugefügt'),
    ).toBeOnTheScreen();
  });

  it('rolls back and reports a failed request', async () => {
    const client = new QueryClient({defaultOptions: {queries: {retry: false}}});
    const finish = mockFavoritesApi(500);
    await renderProbe(client);

    await fireEvent.press(screen.getByTestId('add'));
    await waitFor(() =>
      expect(client.getQueryData(FAVORITES_QUERY.queryKey)).toEqual({
        items: [EVENT],
      }),
    );
    await act(async () => finish());

    expect(await screen.findByText('Das hat nicht geklappt')).toBeOnTheScreen();
    expect(client.getQueryData(FAVORITES_QUERY.queryKey)).toEqual({items: []});
  });
});
