import {QueryClient, QueryClientProvider} from '@tanstack/react-query';
import {fireEvent, screen, waitFor} from '@testing-library/react-native';
import {router} from 'expo-router';
import React from 'react';

import {renderWithProviders} from '@/test-utils';

import type {ModEventDetail} from './form';
import {ModEventFormScreen} from './ModEventFormScreen';

const CATEGORIES = [
  {id: 'c1', name: 'Stadtfest', emoji: '🎪', color: '#FFB547', sortOrder: 0},
];
const PUBLISHED: ModEventDetail = {
  id: 'e1',
  name: 'Aalener Weihnachtsmarkt',
  shortName: 'Weihnachtsmarkt',
  status: 'published',
  categoryId: 'c1',
  startDate: '2026-11-26',
  endDate: '2026-12-23',
  openingHours: ['Mo–Sa 11–20 Uhr'],
  place: 'Marktplatz',
  address: 'Marktplatz, 73430 Aalen',
  city: 'Aalen',
  postalCode: '73430',
  lat: 48.8375,
  lon: 10.0933,
  program: [],
  favoriteCount: 214,
  source: 'manual',
  version: 4,
  images: [],
};

interface Call {
  method: string;
  path: string;
  body: string;
  ifMatch: string | null;
}

type Handler = (call: Call) => {status: number; body?: unknown} | undefined;

function mockApi(handler: Handler = () => undefined): Call[] {
  const calls: Call[] = [];
  jest.spyOn(global, 'fetch').mockImplementation(async input => {
    const request = input as Request;
    const url = new URL(request.url);
    const call = {
      method: request.method,
      path: url.pathname,
      body: await request.text(),
      ifMatch: request.headers.get('If-Match'),
    };
    calls.push(call);
    const json = (body: unknown, status = 200) =>
      new Response(body === undefined ? null : JSON.stringify(body), {
        status,
        headers: {'Content-Type': 'application/json'},
      });
    const custom = handler(call);
    if (custom) return json(custom.body, custom.status);
    if (url.pathname === '/v1/categories') return json(CATEGORIES);
    if (url.pathname === '/v1/mod/geocode/reverse') {
      return json(
        url.searchParams.get('lat') === '0'
          ? {street: null, postalCode: null, city: '', label: ''}
          : {
              street: 'Festplatz 1',
              postalCode: '73433',
              city: 'Aalen',
              label: '73433 Aalen',
            },
      );
    }
    if (url.pathname === '/v1/mod/events/e1' && request.method === 'GET') {
      return json(PUBLISHED);
    }
    return json({error: 'not_found', message: ''}, 404);
  });
  return calls;
}

async function renderForm(eventId: string | null) {
  const client = new QueryClient({defaultOptions: {queries: {retry: false}}});
  await renderWithProviders(
    <QueryClientProvider client={client}>
      <ModEventFormScreen eventId={eventId} />
    </QueryClientProvider>,
  );
  await waitFor(() =>
    expect(screen.getByTestId('mod.form.category.c1')).toBeOnTheScreen(),
  );
}

describe('ModEventFormScreen', () => {
  beforeEach(() => jest.mocked(router.back).mockClear());
  afterEach(() => jest.restoreAllMocks());

  it('marks the missing required fields before publishing (08-06)', async () => {
    const calls = mockApi();
    await renderForm(null);
    expect(screen.getByText('Status: Entwurf')).toBeOnTheScreen();

    await fireEvent.changeText(
      screen.getByTestId('mod.form.name'),
      'Herbstfest',
    );
    await fireEvent.press(screen.getByTestId('mod.form.publish'));

    expect(
      await screen.findByText('Bitte fülle die markierten Pflichtfelder aus'),
    ).toBeOnTheScreen();
    expect(screen.getByText('Bitte wähle eine Kategorie.')).toBeOnTheScreen();
    expect(screen.getByText('Bitte wähle den Beginn.')).toBeOnTheScreen();
    expect(screen.getByText('Bitte wähle das Ende.')).toBeOnTheScreen();
    expect(
      screen.getByText('Bitte gib eine Adresse ein oder setze einen Pin.'),
    ).toBeOnTheScreen();
    expect(calls.some(call => call.path.startsWith('/v1/mod'))).toBe(false);
  });

  it('saves a new draft with only a name', async () => {
    const calls = mockApi(call =>
      call.method === 'POST' && call.path === '/v1/mod/events'
        ? {
            status: 201,
            body: {...PUBLISHED, id: 'new', status: 'draft', version: 1},
          }
        : undefined,
    );
    await renderForm(null);
    await fireEvent.changeText(
      screen.getByTestId('mod.form.name'),
      'Herbstfest',
    );
    await fireEvent.press(screen.getByTestId('mod.form.saveDraft'));

    expect(
      await screen.findByText('Als Entwurf gespeichert'),
    ).toBeOnTheScreen();
    const create = calls.find(call => call.method === 'POST');
    expect(JSON.parse(create?.body ?? '{}')).toMatchObject({
      name: 'Herbstfest',
    });
    expect(router.back).toHaveBeenCalled();
  });

  it('sets the location on the full-screen map and fills the address (08-07)', async () => {
    const calls = mockApi();
    await renderForm(null);
    await fireEvent.press(screen.getByTestId('mod.form.location.pin'));
    expect(screen.getByText('Ort auf der Karte wählen')).toBeOnTheScreen();

    // The map mock reports its center 48.84, 10.09 once it is shown.
    await fireEvent.press(screen.getByTestId('mod.form.picker.confirm'));

    await waitFor(() =>
      expect(screen.getByTestId('mod.form.address')).toHaveDisplayValue(
        'Festplatz 1',
      ),
    );
    const reverse = calls.find(call => call.path === '/v1/mod/geocode/reverse');
    expect(reverse).toBeDefined();
    expect(
      screen.getByText('Tippe, um den Pin zu verschieben'),
    ).toBeOnTheScreen();
  });

  it('replaces a typed address by the pin address in pin mode', async () => {
    mockApi();
    await renderForm(null);
    await fireEvent.changeText(
      screen.getByTestId('mod.form.address'),
      'Marktplatz 1, 73430 Aalen',
    );
    await fireEvent.press(screen.getByTestId('mod.form.location.pin'));
    await fireEvent.press(screen.getByTestId('mod.form.picker.confirm'));

    await waitFor(() =>
      expect(screen.getByTestId('mod.form.address')).toHaveDisplayValue(
        'Festplatz 1',
      ),
    );
  });

  it('uses the coordinates as address when no street is near the pin', async () => {
    mockApi(call =>
      call.path === '/v1/mod/geocode/reverse'
        ? {status: 404, body: {error: 'not_found', message: ''}}
        : undefined,
    );
    await renderForm(null);
    await fireEvent.press(screen.getByTestId('mod.form.location.pin'));
    await fireEvent.press(screen.getByTestId('mod.form.picker.confirm'));

    await waitFor(() =>
      expect(screen.getByTestId('mod.form.address')).toHaveDisplayValue(
        '48.84000, 10.09000',
      ),
    );
  });

  it('suggests places while typing the address and takes the chosen one (08-03)', async () => {
    mockApi(call =>
      call.path === '/v1/geocode'
        ? {
            status: 200,
            body: [
              {
                label: 'Marktplatz 1, 73430 Aalen',
                city: 'Aalen',
                postalCode: '73430',
                lat: 48.8368,
                lon: 10.0932,
                kind: 'address',
              },
            ],
          }
        : undefined,
    );
    await renderForm(null);
    await fireEvent.changeText(
      screen.getByTestId('mod.form.address'),
      'Marktpl',
    );

    await fireEvent.press(
      await screen.findByTestId('mod.form.address.suggestion.0'),
    );

    expect(screen.getByTestId('mod.form.address')).toHaveDisplayValue(
      'Marktplatz 1',
    );
    expect(screen.getByText('48.8368, 10.0932')).toBeOnTheScreen();
    expect(
      screen.queryByTestId('mod.form.address.suggestions'),
    ).not.toBeOnTheScreen();
  });

  it('says so when no place matches the address', async () => {
    mockApi(call =>
      call.path === '/v1/geocode' ? {status: 200, body: []} : undefined,
    );
    await renderForm(null);
    await fireEvent.changeText(
      screen.getByTestId('mod.form.address'),
      'Nirgendwo',
    );

    expect(
      await screen.findByText(
        'Kein Ort gefunden. Setze sonst einen Pin auf der Karte.',
        {},
        // 300 ms debounce plus the request: the 1 s default timed out in a loaded full run.
        {timeout: 3000},
      ),
    ).toBeOnTheScreen();
  });

  it('edits a published event with If-Match and confirms the changes', async () => {
    const calls = mockApi(call =>
      call.method === 'PATCH'
        ? {status: 200, body: {...PUBLISHED, price: 'Frei', version: 5}}
        : undefined,
    );
    await renderForm('e1');
    expect(screen.getByText('Status: Veröffentlicht')).toBeOnTheScreen();
    await fireEvent.changeText(screen.getByTestId('mod.form.price'), 'Frei');
    await fireEvent.press(screen.getByText('Änderungen veröffentlichen'));

    expect(
      await screen.findByText('Änderungen veröffentlicht'),
    ).toBeOnTheScreen();
    const patch = calls.find(call => call.method === 'PATCH');
    expect(patch?.ifMatch).toBe('"4"');
    expect(JSON.parse(patch?.body ?? '{}').price).toBe('Frei');
  });

  it('shows the conflict dialog on a version conflict', async () => {
    mockApi(call =>
      call.method === 'PATCH'
        ? {status: 409, body: {error: 'version_conflict', message: ''}}
        : undefined,
    );
    await renderForm('e1');
    await fireEvent.press(screen.getByTestId('mod.form.publish'));
    expect(
      await screen.findByText('Dieses Fest wurde inzwischen geändert'),
    ).toBeOnTheScreen();
  });

  it('cancels a published event with a reason (08-08, 08-09)', async () => {
    const calls = mockApi(call =>
      call.path === '/v1/mod/events/e1/cancel'
        ? {status: 200, body: {...PUBLISHED, status: 'cancelled', version: 5}}
        : undefined,
    );
    await renderForm('e1');
    await fireEvent.press(screen.getByTestId('mod.form.menu'));
    await fireEvent.press(screen.getByTestId('mod.form.menu.cancel'));
    expect(
      screen.getByText(
        '„Aalener Weihnachtsmarkt“ wird als abgesagt markiert. 214 Nutzer mit diesem Favoriten werden benachrichtigt.',
      ),
    ).toBeOnTheScreen();

    await fireEvent.changeText(
      screen.getByTestId('mod.cancelDialog.reason'),
      'Sturmwarnung',
    );
    await fireEvent.press(screen.getByTestId('mod.cancelDialog.confirm'));

    expect(
      await screen.findByText('Abgesagt · 214 Nutzer werden benachrichtigt'),
    ).toBeOnTheScreen();
    const cancel = calls.find(call => call.path.endsWith('/cancel'));
    expect(JSON.parse(cancel?.body ?? '{}')).toEqual({reason: 'Sturmwarnung'});
  });

  it('warns that favorites are not notified when deleting (08-10)', async () => {
    const calls = mockApi(call =>
      call.method === 'DELETE' ? {status: 204} : undefined,
    );
    await renderForm('e1');
    await fireEvent.press(screen.getByTestId('mod.form.menu'));
    await fireEvent.press(screen.getByTestId('mod.form.menu.delete'));
    expect(
      screen.getByText(/zum Informieren besser absagen/),
    ).toBeOnTheScreen();

    await fireEvent.press(screen.getByTestId('mod.deleteDialog.confirm'));

    expect(await screen.findByText('Fest gelöscht')).toBeOnTheScreen();
    expect(calls.some(call => call.method === 'DELETE')).toBe(true);
  });
});
