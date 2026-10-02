import {QueryClient, QueryClientProvider} from '@tanstack/react-query';
import {act, fireEvent, screen, waitFor} from '@testing-library/react-native';
import {router} from 'expo-router';
import React from 'react';

import {useAuth} from '@/features/auth/AuthProvider';
import {renderWithProviders} from '@/test-utils';

import {ModEventsScreen} from '../ModEventsScreen';
import type {ModEventDetail} from '../form';
import {AiSearch, AiSearchProvider, POLL_MS} from './AiSearchProvider';
import {ReviewScreen} from './ReviewScreen';

jest.mock('@/features/auth/AuthProvider', () => ({useAuth: jest.fn()}));
jest.mock('expo-router', () => {
  const actual = jest.requireActual('expo-router');
  return {
    ...actual,
    router: {
      push: jest.fn(),
      back: jest.fn(),
      replace: jest.fn(),
      canGoBack: jest.fn(() => true),
    },
    useFocusEffect: jest.fn(),
  };
});

const CATEGORY = {
  id: 'c1',
  name: 'Stadtfest',
  emoji: '🎪',
  color: '#FFB547',
  sortOrder: 0,
};
const JOB: AiSearch = {
  id: 'j1',
  postalCode: '73430',
  placeName: 'Aalen',
  status: 'running',
  createdAt: '2026-10-02T09:00:00Z',
  newEventIds: [],
  skipped: {duplicate: 0, outOfRegion: 0, invalid: 0, unverifiedSource: 0},
};
const DONE: AiSearch = {
  ...JOB,
  status: 'completed',
  newEventIds: ['e1', 'e2', 'e3'],
};

function find(
  id: string,
  changes: Partial<ModEventDetail> = {},
): ModEventDetail {
  return {
    id,
    regionId: 'r1',
    name: `Fund ${id}`,
    shortName: `Fund ${id}`,
    status: 'draft',
    categoryId: 'c1',
    startDate: '2026-10-17',
    endDate: '2026-10-18',
    openingHours: [],
    place: 'Marktplatz',
    address: 'Marktplatz 1',
    city: 'Aalen',
    postalCode: '73430',
    lat: 48.8,
    lon: 10.1,
    program: [],
    favoriteCount: 0,
    source: 'ai',
    sourceUrl: `https://www.aalen.de/${id}`,
    version: 1,
    images: [],
    ...changes,
  };
}

interface Call {
  method: string;
  path: string;
  search: string;
  body: string;
}

type Handler = (call: Call) => {status: number; body?: unknown} | undefined;

function mockApi(handler: Handler): Call[] {
  const calls: Call[] = [];
  jest.spyOn(global, 'fetch').mockImplementation(async input => {
    const request = input as Request;
    const url = new URL(request.url);
    const call = {
      method: request.method,
      path: url.pathname,
      search: decodeURIComponent(url.search),
      body: request.method === 'GET' ? '' : await request.text(),
    };
    calls.push(call);
    const json = (body: unknown, status = 200) =>
      new Response(body === undefined ? null : JSON.stringify(body), {
        status,
        headers: {'Content-Type': 'application/json'},
      });
    const custom = handler(call);
    if (custom) return json(custom.body, custom.status);
    if (call.path === '/v1/categories') return json([CATEGORY]);
    if (call.path === '/v1/mod/events' && call.method === 'GET')
      return json({items: []});
    if (call.path === '/v1/mod/ai-searches' && call.method === 'GET')
      return json([]);
    return json({error: 'not_found', message: ''}, 404);
  });
  return calls;
}

async function render(ui: React.ReactElement) {
  jest
    .mocked(useAuth)
    .mockReturnValue({isModerator: true} as ReturnType<typeof useAuth>);
  const client = new QueryClient({defaultOptions: {queries: {retry: false}}});
  await renderWithProviders(
    <QueryClientProvider client={client}>
      <AiSearchProvider>{ui}</AiSearchProvider>
    </QueryClientProvider>,
  );
}

describe('AI search in the overview (09-01 to 09-03)', () => {
  afterEach(() => {
    jest.restoreAllMocks();
    jest.useRealTimers();
  });

  it('validates the postal code, shows the place and starts the search', async () => {
    const calls = mockApi(call => {
      if (call.path === '/v1/geocode') {
        return {
          status: 200,
          body: [
            {
              label: '73430 Aalen',
              city: 'Aalen',
              postalCode: '73430',
              lat: 48.8,
              lon: 10.1,
              kind: 'postcode',
            },
          ],
        };
      }
      if (call.path === '/v1/mod/ai-searches' && call.method === 'POST') {
        return {status: 202, body: {...JOB, status: 'queued'}};
      }
      return undefined;
    });
    await render(<ModEventsScreen />);

    await fireEvent.press(screen.getByTestId('mod.events.aiSearch'));
    await fireEvent.changeText(
      screen.getByTestId('mod.ai.postalCode'),
      '73a43',
    );
    expect(screen.getByTestId('mod.ai.postalCode')).toHaveDisplayValue('7343');
    expect(screen.getByTestId('mod.ai.start')).toBeDisabled();

    await fireEvent.changeText(
      screen.getByTestId('mod.ai.postalCode'),
      '73430',
    );
    expect(await screen.findByTestId('mod.ai.place')).toHaveTextContent(
      'Aalen',
    );
    await fireEvent.press(screen.getByTestId('mod.ai.start'));

    expect(
      await screen.findByText('Suche läuft für 73430 Aalen …'),
    ).toBeOnTheScreen();
    const start = calls.find(c => c.method === 'POST');
    expect(JSON.parse(start?.body ?? '{}')).toEqual({postalCode: '73430'});
  });

  it('says so when the postal code is unknown', async () => {
    mockApi(call =>
      call.path === '/v1/geocode' ? {status: 200, body: []} : undefined,
    );
    await render(<ModEventsScreen />);
    await fireEvent.press(screen.getByTestId('mod.events.aiSearch'));
    await fireEvent.changeText(
      screen.getByTestId('mod.ai.postalCode'),
      '99999',
    );

    expect(
      await screen.findByText('Diese Postleitzahl kennen wir nicht.'),
    ).toBeOnTheScreen();
    expect(screen.getByTestId('mod.ai.start')).toBeDisabled();
  });

  it('restores a running search, polls every 10 s and offers the review', async () => {
    jest.useFakeTimers();
    let status: AiSearch = JOB;
    mockApi(call => {
      if (call.path === '/v1/mod/ai-searches' && call.method === 'GET') {
        return {status: 200, body: [JOB]};
      }
      if (call.path === '/v1/mod/ai-searches/j1')
        return {status: 200, body: status};
      return undefined;
    });
    await render(<ModEventsScreen />);
    expect(
      await screen.findByText('Suche läuft für 73430 Aalen …'),
    ).toBeOnTheScreen();

    status = DONE;
    await act(async () => {
      jest.advanceTimersByTime(POLL_MS);
    });

    expect(
      await screen.findByText('3 neue Entwürfe aus der Suche für 73430'),
    ).toBeOnTheScreen();
    await fireEvent.press(screen.getByTestId('mod.ai.banner.review'));
    expect(router.push).toHaveBeenCalledWith('/mod/pruefen/j1');
  });

  it('shows a failed search with retry', async () => {
    jest.useFakeTimers();
    let status: AiSearch = JOB;
    const calls = mockApi(call => {
      if (call.path === '/v1/mod/ai-searches' && call.method === 'GET') {
        return {status: 200, body: [JOB]};
      }
      if (call.path === '/v1/mod/ai-searches/j1')
        return {status: 200, body: status};
      if (call.path === '/v1/mod/ai-searches' && call.method === 'POST') {
        return {status: 202, body: {...JOB, id: 'j2', status: 'queued'}};
      }
      return undefined;
    });
    await render(<ModEventsScreen />);
    expect(
      await screen.findByText('Suche läuft für 73430 Aalen …'),
    ).toBeOnTheScreen();

    status = {...JOB, status: 'failed', errorCode: 'timeout'};
    await act(async () => {
      jest.advanceTimersByTime(POLL_MS);
    });
    expect(await screen.findByText('Suche fehlgeschlagen')).toBeOnTheScreen();

    await fireEvent.press(screen.getByTestId('mod.ai.banner.retry'));
    await waitFor(() =>
      expect(calls.some(c => c.method === 'POST')).toBe(true),
    );
  });
});

describe('ReviewScreen (09-04, 09-05)', () => {
  afterEach(() => jest.restoreAllMocks());

  it('publishes, discards and opens the form, then summarizes', async () => {
    const calls = mockApi(call => {
      if (call.path === '/v1/mod/ai-searches/j1')
        return {status: 200, body: DONE};
      if (call.path === '/v1/mod/events' && call.method === 'GET') {
        return {
          status: 200,
          body: {
            items: ['e1', 'e2', 'e3'].map(id => ({
              id,
              name: id,
              status: 'draft',
              place: '',
              city: '',
              favoriteCount: 0,
              source: 'ai',
              version: 1,
            })),
          },
        };
      }
      const detail = /^\/v1\/mod\/events\/(e\d)$/.exec(call.path);
      if (detail && call.method === 'GET') {
        return {
          status: 200,
          body:
            detail[1] === 'e3'
              ? find('e3', {categoryId: null})
              : find(detail[1] ?? ''),
        };
      }
      if (call.path === '/v1/mod/events/e1/publish') {
        return {status: 200, body: find('e1', {status: 'published'})};
      }
      if (call.method === 'DELETE') return {status: 204};
      return undefined;
    });
    await render(<ReviewScreen jobId="j1" />);

    expect(await screen.findByText('Fund 1 von 3')).toBeOnTheScreen();
    expect(await screen.findByText('aalen.de/e1')).toBeOnTheScreen();
    await fireEvent.press(screen.getByTestId('mod.review.publish'));

    expect(await screen.findByText('Fund 2 von 3')).toBeOnTheScreen();
    expect(await screen.findByText('Fund e2')).toBeOnTheScreen();
    await fireEvent.press(screen.getByTestId('mod.review.discard'));

    expect(await screen.findByText('Fund 3 von 3')).toBeOnTheScreen();
    // Missing category: shown as "fehlt", publishing opens the form instead.
    expect(await screen.findByText('fehlt')).toBeOnTheScreen();
    expect(screen.getByText('Fund e3')).toBeOnTheScreen();
    await fireEvent.press(screen.getByTestId('mod.review.publish'));
    await waitFor(() =>
      expect(router.push).toHaveBeenCalledWith('/mod/fest/e3'),
    );
    expect(calls.some(c => c.path === '/v1/mod/events/e3/publish')).toBe(false);
    expect(
      calls.some(c => c.method === 'DELETE' && c.path.endsWith('/e2')),
    ).toBe(true);
    // The query used the comma form of `ids`.
    expect(calls.some(c => c.search === '?ids=e1,e2,e3')).toBe(true);
  });

  it('pauses with ✕', async () => {
    mockApi(call => {
      if (call.path === '/v1/mod/ai-searches/j1')
        return {status: 200, body: DONE};
      return undefined;
    });
    await render(<ReviewScreen jobId="j1" />);
    await fireEvent.press(await screen.findByTestId('mod.review.close'));

    expect(
      await screen.findByText('Pausiert · offene Funde bleiben als Entwurf'),
    ).toBeOnTheScreen();
    expect(router.back).toHaveBeenCalled();
  });
});
