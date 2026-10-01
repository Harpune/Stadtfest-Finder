import {QueryClient, QueryClientProvider} from '@tanstack/react-query';
import {act, fireEvent, screen, waitFor} from '@testing-library/react-native';
import * as Location from 'expo-location';
import {router} from 'expo-router';
import React from 'react';

import {AuthProvider} from '@/features/auth/AuthProvider';
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
      <AuthProvider>
        <StartScreen />
      </AuthProvider>
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
      expect(screen.getByTestId('discover.pin.e1')).toBeOnTheScreen(),
    );
    expect(screen.getByTestId('discover.chip.c1')).toHaveTextContent(
      /Stadtfest\s*1/,
    );

    // The search loads a padded, grid-snapped area; the count uses the visible area.
    const search = requests.find(r => r.pathname === '/v1/events');
    expect(search?.searchParams.get('bbox')).toBe('9,48,11,49.5');
    const count = requests.find(r => r.pathname === '/v1/events/count');
    expect(count?.searchParams.get('bbox')).toBe('9.6,48.6,10.6,49.1');
    // The first page has no cursor (regression: `cursor=0` was rejected with 422).
    expect(search?.searchParams.get('cursor')).toBeNull();
    expect(search?.searchParams.get('limit')).toBe('500');
    // No position and no radius are sent; distances are computed on the device.
    expect(search?.searchParams.get('lat')).toBeNull();
    expect(search?.searchParams.get('radiusKm')).toBeNull();
  });

  it('keeps data when switching to the list and back without reloading', async () => {
    mockApi(api());
    await renderScreen();
    await settle();
    await waitFor(() =>
      expect(screen.getByTestId('discover.pin.e1')).toBeOnTheScreen(),
    );
    // Only event requests count: the list additionally loads the area name.
    const eventRequests = () =>
      requests.filter(r => r.pathname.startsWith('/v1/events')).length;
    const before = eventRequests();

    await fireEvent.press(screen.getByTestId('discover.toggle.list'));
    expect(screen.getByText('1 Fest im Kartenausschnitt')).toBeOnTheScreen();
    await fireEvent.press(screen.getByTestId('discover.toggle.map'));
    expect(eventRequests()).toBe(before);
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

  it('offers zooming out when the map area has no events', async () => {
    const camera = (
      globalThis as unknown as {mockCameraApi: {zoomTo: jest.Mock}}
    ).mockCameraApi;
    camera.zoomTo.mockClear();
    mockApi(api([]));
    await renderScreen();
    await settle();
    await waitFor(() =>
      expect(
        screen.getByText('Keine Feste in diesem Kartenausschnitt'),
      ).toBeOnTheScreen(),
    );
    await fireEvent.press(screen.getByTestId('discover.empty.zoomOut'));
    expect(camera.zoomTo).toHaveBeenCalledWith(8, expect.anything());
  });

  it('lists only events in the visible area', async () => {
    const outside = {
      ...EVENT,
      id: 'e2',
      name: 'Ulmer Donaufest',
      lat: 48.4,
      lon: 9.99,
    };
    mockApi(api([EVENT, outside]));
    await renderScreen();
    await settle();
    await waitFor(() =>
      expect(screen.getByTestId('discover.pin.e1')).toBeOnTheScreen(),
    );
    await fireEvent.press(screen.getByTestId('discover.toggle.list'));
    expect(screen.getByText('Reichsstädter Tage')).toBeOnTheScreen();
    expect(screen.queryByText('Ulmer Donaufest')).toBeNull();
  });

  it('suggests jumping to a place found by the search text', async () => {
    const camera = (
      globalThis as unknown as {mockCameraApi: {flyTo: jest.Mock}}
    ).mockCameraApi;
    camera.flyTo.mockClear();
    mockApi(url =>
      url.pathname === '/v1/geocode'
        ? {
            status: 200,
            body: [
              {
                label: '89073 Ulm',
                postalCode: '89073',
                city: 'Ulm',
                lat: 48.4,
                lon: 9.99,
                kind: 'postcode',
              },
            ],
          }
        : api([])(url),
    );
    await renderScreen();
    await fireEvent.changeText(
      screen.getByTestId('discover.search.input'),
      'Ulm',
    );
    await settle();
    await fireEvent.press(await screen.findByTestId('discover.place.jump'));
    expect(screen.getByTestId('discover.search.input')).toHaveDisplayValue('');
    expect(camera.flyTo).toHaveBeenCalledWith(
      expect.objectContaining({center: [9.99, 48.4], zoom: 11}),
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

  it('shows name and date on the first pin tap and opens the detail on the second', async () => {
    jest.mocked(router.push).mockClear();
    mockApi(api());
    await renderScreen();
    await settle();
    await waitFor(() =>
      expect(screen.getByTestId('discover.pin.e1')).toBeOnTheScreen(),
    );
    // No carousel: the map keeps the whole screen (decision 01.10.2026).
    expect(screen.queryByTestId('discover.carousel')).toBeNull();

    await fireEvent.press(screen.getByTestId('discover.pin.e1'));
    const selected = screen.getByTestId('discover.pin.selected.e1');
    expect(selected).toHaveTextContent(/Reichsstädter/);
    expect(selected).toHaveTextContent(/1\. Jan – 31\. Dez/);
    expect(router.push).not.toHaveBeenCalled();

    await fireEvent.press(selected);
    expect(router.push).toHaveBeenCalledWith('/f/e1');
  });

  it('lists festivals at the same spot instead of zooming', async () => {
    jest.mocked(router.push).mockClear();
    const sameSquare = {
      ...EVENT,
      id: 'e2',
      name: 'Weinfest am Marktplatz',
      lat: EVENT.lat + 0.00001,
    };
    mockApi(api([EVENT, sameSquare]));
    await renderScreen();
    await settle();
    await waitFor(() =>
      expect(screen.getByTestId('discover.cluster.c:e1')).toBeOnTheScreen(),
    );

    await fireEvent.press(screen.getByTestId('discover.cluster.c:e1'));

    expect(screen.getByText('2 Feste an diesem Ort')).toBeOnTheScreen();
    expect(screen.getByText('Weinfest am Marktplatz')).toBeOnTheScreen();
    await fireEvent.press(screen.getByTestId('discover.stack.item.e2'));
    expect(router.push).toHaveBeenCalledWith('/f/e2');
  });

  it('clears the selection when the map itself is tapped', async () => {
    mockApi(api());
    await renderScreen();
    await settle();
    await waitFor(() =>
      expect(screen.getByTestId('discover.pin.e1')).toBeOnTheScreen(),
    );
    await fireEvent.press(screen.getByTestId('discover.pin.e1'));
    expect(screen.getByTestId('discover.pin.selected.e1')).toBeOnTheScreen();
    // Map presses right after a marker press belong to that marker press (DiscoverMap).
    await act(async () => {
      await new Promise(resolve => setTimeout(resolve, 200));
    });

    await fireEvent.press(screen.getByTestId('discover.map'));
    await waitFor(() =>
      expect(screen.queryByTestId('discover.pin.selected.e1')).toBeNull(),
    );
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
      expect(screen.getByTestId('discover.pin.e1')).toBeOnTheScreen(),
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
