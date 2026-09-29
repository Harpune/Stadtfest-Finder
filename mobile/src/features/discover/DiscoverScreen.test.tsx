import {QueryClient, QueryClientProvider} from '@tanstack/react-query';
import {act, fireEvent, screen, waitFor} from '@testing-library/react-native';
import * as Location from 'expo-location';
import React from 'react';

import {renderWithProviders} from '@/test-utils';

import StartScreen from '@/app/index';

const CATEGORIES = [
  {id: 'c1', name: 'Stadtfest', emoji: '🎪', color: '#FFB547', sortOrder: 0},
  {
    id: 'c2',
    name: 'Weihnachtsmarkt',
    emoji: '🎄',
    color: '#5EEAD4',
    sortOrder: 1,
  },
];
const EVENT = {
  id: 'e1',
  name: 'Reichsstädter Tage',
  shortName: 'Reichsstädter',
  status: 'published',
  startDate: '2026-01-01',
  endDate: '2099-12-31',
  place: 'Marktplatz',
  city: 'Aalen',
  lat: 48.84,
  lon: 10.09,
  categoryId: 'c1',
  distanceKm: 1.4,
};

/** Minimal URL parsing: React Native's URL polyfill lacks pathname/searchParams. */
interface ParsedUrl {
  pathname: string;
  searchParams: {get: (key: string) => string | null};
}

function parseUrl(raw: string): ParsedUrl {
  const [base = '', query = ''] = raw.split('?');
  const pathname = base.replace(/^https?:\/\/[^/]+/, '');
  const params = new Map<string, string>();
  for (const pair of query.split('&').filter(Boolean)) {
    const [key = '', value = ''] = pair.split('=');
    params.set(decodeURIComponent(key), decodeURIComponent(value));
  }
  return {pathname, searchParams: {get: key => params.get(key) ?? null}};
}

type Handler = (url: ParsedUrl) => {status: number; body?: unknown};
let requests: ParsedUrl[] = [];

function mockApi(handler: Handler) {
  requests = [];
  jest
    .spyOn(global, 'fetch')
    .mockImplementation(async (input: RequestInfo | URL) => {
      const url = parseUrl(
        input instanceof Request ? input.url : String(input),
      );
      requests.push(url);
      const {status, body} = handler(url);
      return new Response(body === undefined ? null : JSON.stringify(body), {
        status,
        headers: {'Content-Type': 'application/json'},
      });
    });
}

function api(events: unknown[] = [EVENT]): Handler {
  return url => {
    if (url.pathname === '/v1/categories')
      return {status: 200, body: CATEGORIES};
    if (url.pathname === '/v1/events/count') {
      return {
        status: 200,
        body: {total: events.length, byCategory: {c1: events.length}},
      };
    }
    if (url.pathname === '/v1/events')
      return {status: 200, body: {items: events, nextCursor: null}};
    return {status: 404, body: {error: 'not_found', message: ''}};
  };
}

async function renderScreen() {
  const client = new QueryClient({defaultOptions: {queries: {retry: false}}});
  await renderWithProviders(
    <QueryClientProvider client={client}>
      <StartScreen />
    </QueryClientProvider>,
  );
}

describe('Discover screen', () => {
  afterEach(() => jest.restoreAllMocks());

  /** Waits past the 300 ms debounce of search, viewport and filter preview. */
  async function settle() {
    await act(async () => {
      await new Promise(resolve => setTimeout(resolve, 400));
    });
  }

  it('loads events for the viewport and shows chips with counts', async () => {
    mockApi(api());
    await renderScreen();
    await settle();
    await waitFor(() =>
      expect(screen.getByText('Reichsstädter Tage')).toBeOnTheScreen(),
    );
    expect(screen.getByTestId('discover.chip.c1')).toHaveTextContent(
      /Stadtfest\s*1/,
    );

    const search = requests.find(r => r.pathname === '/v1/events');
    expect(search?.searchParams.get('bbox')).toBe('9.6,48.6,10.6,49.1');
    // The first page has no cursor (regression: `cursor=0` was rejected with 422).
    expect(search?.searchParams.get('cursor')).toBeNull();
    expect(search?.searchParams.get('limit')).toBe('500');
    // Without location access the distance refers to the map center.
    expect(search?.searchParams.get('lat')).toBe('48.84');
  });

  it('keeps data when switching to the list and back without reloading', async () => {
    mockApi(api());
    await renderScreen();
    await settle();
    await waitFor(() =>
      expect(screen.getByText('Reichsstädter Tage')).toBeOnTheScreen(),
    );
    const before = requests.length;

    await fireEvent.press(screen.getByTestId('discover.toggle.list'));
    expect(screen.getByText('1 Fest · bis 150 km')).toBeOnTheScreen();
    await fireEvent.press(screen.getByTestId('discover.toggle.map'));
    expect(requests.length).toBe(before);
  });

  it('filters by category chip', async () => {
    mockApi(api());
    await renderScreen();
    await settle();
    await waitFor(() =>
      expect(screen.getByTestId('discover.chip.c2')).toBeOnTheScreen(),
    );
    await fireEvent.press(screen.getByTestId('discover.chip.c2'));
    await settle();
    await waitFor(() =>
      expect(
        requests.some(r => r.searchParams.get('categories') === 'c2'),
      ).toBe(true),
    );
    expect(screen.getByTestId('discover.filter.open.badge')).toHaveTextContent(
      '1',
    );
  });

  it('shows the empty state and resets filter and search', async () => {
    mockApi(api([]));
    await renderScreen();
    await settle();
    await waitFor(() =>
      expect(screen.getByText('Keine Feste im Umkreis')).toBeOnTheScreen(),
    );
    await fireEvent.press(screen.getByTestId('discover.empty.expand'));
    await settle();
    await waitFor(() =>
      expect(requests.some(r => r.searchParams.get('radiusKm') === '300')).toBe(
        true,
      ),
    );
  });

  it('shows a search without results', async () => {
    mockApi(api([]));
    await renderScreen();
    await fireEvent.changeText(
      screen.getByTestId('discover.search.input'),
      'Reichstätter',
    );
    await settle();
    await waitFor(() =>
      expect(
        screen.getByText('Kein Fest für „Reichstätter“'),
      ).toBeOnTheScreen(),
    );
  });

  it('centers the map on a carousel card on the first tap', async () => {
    const camera = (
      globalThis as unknown as {mockCameraApi: {easeTo: jest.Mock}}
    ).mockCameraApi;
    camera.easeTo.mockClear();
    mockApi(api());
    await renderScreen();
    await settle();
    await waitFor(() =>
      expect(screen.getByTestId('discover.carousel.card.e1')).toBeOnTheScreen(),
    );
    await fireEvent.press(screen.getByTestId('discover.carousel.card.e1'));
    expect(camera.easeTo).toHaveBeenCalledWith(
      expect.objectContaining({center: [10.09, 48.84]}),
    );
    expect(screen.getByTestId('discover.carousel.card.e1')).toBeSelected();

    // The second tap opens the detail (placeholder) instead of moving again.
    camera.easeTo.mockClear();
    await fireEvent.press(screen.getByTestId('discover.carousel.card.e1'));
    expect(camera.easeTo).not.toHaveBeenCalled();
    expect(
      screen.getByText('Die Detailseite folgt in Kürze.'),
    ).toBeOnTheScreen();
  });

  it('clears the selection when the map itself is tapped', async () => {
    mockApi(api());
    await renderScreen();
    await settle();
    await waitFor(() =>
      expect(screen.getByTestId('discover.carousel.card.e1')).toBeOnTheScreen(),
    );
    await fireEvent.press(screen.getByTestId('discover.carousel.card.e1'));
    expect(screen.getByTestId('discover.pin.selected.e1')).toBeOnTheScreen();

    await fireEvent.press(screen.getByTestId('discover.map'));
    await waitFor(() =>
      expect(screen.queryByTestId('discover.pin.selected.e1')).toBeNull(),
    );
    expect(screen.getByTestId('discover.carousel.card.e1')).not.toBeSelected();
  });

  it('does not hang when location is granted but no GPS fix arrives', async () => {
    jest
      .mocked(Location.requestForegroundPermissionsAsync)
      .mockResolvedValueOnce({
        granted: true,
      } as Location.LocationPermissionResponse);
    jest
      .mocked(Location.getCurrentPositionAsync)
      .mockReturnValueOnce(
        new Promise<Location.LocationObject>(() => undefined),
      );
    mockApi(api());
    await renderScreen();
    await act(async () => {
      await new Promise(resolve => setTimeout(resolve, 3500));
    });
    await waitFor(() =>
      expect(screen.getByText('Reichsstädter Tage')).toBeOnTheScreen(),
    );
  }, 15000);

  it('shows a toast with retry when loading fails', async () => {
    mockApi(url =>
      url.pathname === '/v1/events'
        ? {status: 500, body: {error: 'internal_error', message: ''}}
        : api()(url),
    );
    await renderScreen();
    await settle();
    await waitFor(() =>
      expect(
        screen.getByText('Feste konnten nicht geladen werden'),
      ).toBeOnTheScreen(),
    );
    expect(screen.getByText('Erneut versuchen')).toBeOnTheScreen();
  });
});
