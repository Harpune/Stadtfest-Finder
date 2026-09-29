import {QueryClient, QueryClientProvider} from '@tanstack/react-query';
import {fireEvent, screen, waitFor} from '@testing-library/react-native';
import {router} from 'expo-router';
import * as WebBrowser from 'expo-web-browser';
import React from 'react';
import {Linking} from 'react-native';

import {AuthProvider} from '@/features/auth/AuthProvider';
import {renderWithProviders} from '@/test-utils';

import {EventDetailScreen} from './EventDetailScreen';

const CATEGORY = {id: 'c1', name: 'Stadtfest', emoji: '🎪', color: '#FFB547'};
const DETAIL = {
  id: 'e1',
  name: 'Reichsstädter Tage',
  shortName: 'Reichsstädter',
  status: 'published',
  cancelReason: null,
  category: CATEGORY,
  startDate: '2026-01-01',
  endDate: '2099-12-31',
  openingHours: ['Mo–Do 11–23 Uhr', 'Fr–Sa 11–1 Uhr'],
  price: 'Frei',
  place: 'Marktplatz',
  address: 'Marktplatz 1',
  city: 'Aalen',
  postalCode: '73430',
  lat: 48.8368,
  lon: 10.0932,
  description: 'Das große Stadtfest in der Altstadt.',
  program: [
    {
      date: '2026-09-26',
      timeLabel: '10:45 Uhr',
      title: 'Umzug',
      subtitle: 'Start am Bahnhof',
    },
  ],
  transit: 'Bahnhof Aalen, 5 Minuten zu Fuß',
  parking: null,
  websiteUrl: 'https://www.aalen.de/reichsstaedter-tage',
  images: [],
  distanceKm: null,
};

function mockApi(detail: object | null, status = 200) {
  jest
    .spyOn(global, 'fetch')
    .mockImplementation(async (input: RequestInfo | URL) => {
      const url = input instanceof Request ? input.url : String(input);
      if (url.includes('/v1/categories')) {
        return new Response(JSON.stringify([{...CATEGORY, sortOrder: 0}]), {
          status: 200,
        });
      }
      return new Response(
        detail === null
          ? JSON.stringify({error: 'not_found', message: ''})
          : JSON.stringify(detail),
        {
          status,
          headers: {'Content-Type': 'application/json'},
        },
      );
    });
}

async function renderDetail() {
  const client = new QueryClient({defaultOptions: {queries: {retry: false}}});
  await renderWithProviders(
    <QueryClientProvider client={client}>
      <AuthProvider>
        <EventDetailScreen eventId="e1" />
      </AuthProvider>
    </QueryClientProvider>,
  );
}

describe('EventDetailScreen', () => {
  afterEach(() => jest.restoreAllMocks());

  it('shows header, info, sections and the website', async () => {
    mockApi(DETAIL);
    await renderDetail();
    await waitFor(() =>
      expect(screen.getByTestId('detail.about')).toBeOnTheScreen(),
    );
    expect(screen.getByTestId('detail.title')).toHaveTextContent(
      'Reichsstädter Tage',
    );
    expect(screen.getByText('Fr–Sa 11–1 Uhr')).toBeOnTheScreen();
    expect(screen.getByText('Umzug')).toBeOnTheScreen();
    expect(screen.getByText('10:45 Uhr · Start am Bahnhof')).toBeOnTheScreen();
    expect(
      screen.getByText('Marktplatz, Marktplatz 1, 73430 Aalen'),
    ).toBeOnTheScreen();
    expect(screen.getByText('aalen.de')).toBeOnTheScreen();

    await fireEvent.press(screen.getByTestId('detail.website'));
    expect(WebBrowser.openBrowserAsync).toHaveBeenCalledWith(
      'https://www.aalen.de/reichsstaedter-tage',
    );
  });

  it('omits empty sections and unsafe websites', async () => {
    mockApi({
      ...DETAIL,
      description: null,
      program: [],
      transit: null,
      parking: null,
      openingHours: [],
      price: null,
      websiteUrl: 'javascript:alert(1)',
    });
    await renderDetail();
    await waitFor(() =>
      expect(screen.getByTestId('detail.place')).toBeOnTheScreen(),
    );
    expect(screen.queryByTestId('detail.about')).toBeNull();
    expect(screen.queryByTestId('detail.program')).toBeNull();
    expect(screen.queryByTestId('detail.directions')).toBeNull();
    expect(screen.queryByTestId('detail.website')).toBeNull();
    expect(screen.queryByText('Öffnungszeiten')).toBeNull();
  });

  it('shows cancelled events with reason and disables inviting', async () => {
    mockApi({...DETAIL, status: 'cancelled', cancelReason: 'Unwetterwarnung'});
    await renderDetail();
    await waitFor(() =>
      expect(screen.getByTestId('detail.cancelReason')).toHaveTextContent(
        'Grund: Unwetterwarnung',
      ),
    );
    expect(screen.getByTestId('detail.status')).toHaveTextContent('Abgesagt');
    expect(screen.getByTestId('detail.invite')).toBeDisabled();
    expect(screen.getByTestId('detail.route')).not.toBeDisabled();
  });

  it('shows the not-found hint on 404 and goes back to the map', async () => {
    mockApi(null, 404);
    await renderDetail();
    await waitFor(() =>
      expect(
        screen.getByText('Dieses Fest ist nicht mehr verfügbar'),
      ).toBeOnTheScreen(),
    );
    await fireEvent.press(screen.getByTestId('detail.toMap'));
    expect(router.back).toHaveBeenCalled();
  });

  it('opens the guest hint for favorite, share and invite', async () => {
    mockApi(DETAIL);
    await renderDetail();
    await waitFor(() =>
      expect(screen.getByTestId('detail.title')).toBeOnTheScreen(),
    );
    await fireEvent.press(screen.getByTestId('detail.favorite'));
    expect(screen.getByText('Lieblingsfeste merken')).toBeOnTheScreen();
    await fireEvent.press(screen.getByTestId('guestHint.dismiss'));
    await fireEvent.press(screen.getByTestId('detail.share'));
    expect(await screen.findByText('Feste teilen')).toBeOnTheScreen();
  });

  it('starts the route in the maps app', async () => {
    const openURL = jest.spyOn(Linking, 'openURL').mockResolvedValue(true);
    mockApi(DETAIL);
    await renderDetail();
    await waitFor(() =>
      expect(screen.getByTestId('detail.title')).toBeOnTheScreen(),
    );
    await fireEvent.press(screen.getByTestId('detail.route'));
    expect(openURL).toHaveBeenCalledWith(
      expect.stringContaining('48.8368,10.0932'),
    );
  });
});
