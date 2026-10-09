import {QueryClient, QueryClientProvider} from '@tanstack/react-query';
import {fireEvent, screen, waitFor} from '@testing-library/react-native';
import {router} from 'expo-router';
import React from 'react';
import {Alert, AlertButton} from 'react-native';

import {useAuth} from '@/features/auth/AuthProvider';
import {renderWithProviders} from '@/test-utils';

import {ListDetailScreen} from './ListDetailScreen';
import {ListsScreen} from './ListsScreen';
import type {ListEvent, SharedList} from './useLists';

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

const ME = '00000000-0000-4000-8000-000000000001';
const JONAS = '00000000-0000-4000-8000-000000000002';
const MIA = '00000000-0000-4000-8000-000000000003';
const LIST = '00000000-0000-4000-8000-0000000000aa';

function event(
  id: string,
  name: string,
  start: string,
  end: string,
): ListEvent {
  return {
    id,
    name,
    shortName: name,
    status: 'published',
    startDate: start,
    endDate: end,
    place: 'Markt',
    city: 'Ulm',
    lat: 48.4,
    lon: 10,
    categoryId: 'c1',
    categoryName: 'Weihnachtsmarkt',
    emoji: '🎄',
    addedAt: '2026-10-09T12:00:00Z',
  };
}

const TOUR: SharedList = {
  id: LIST,
  name: 'Weihnachtsmarkt-Tour 2026',
  members: [
    {id: JONAS, firstName: 'Jonas', lastName: 'Weber'},
    {id: ME, firstName: 'Lena', lastName: 'Hennig'},
    {id: MIA, firstName: 'Mia', lastName: 'Schulz'},
  ],
  events: [
    event('e1', 'Ulmer Weihnachtsmarkt', '2026-11-23', '2026-12-22'),
    event('e2', 'Augsburger Christkindlesmarkt', '2026-11-23', '2026-12-24'),
  ],
};

interface Call {
  method: string;
  path: string;
  body: string;
}

type Reply = {status: number; body?: unknown};

function mockApi(handler: (call: Call) => Reply | undefined): Call[] {
  const calls: Call[] = [];
  jest.spyOn(global, 'fetch').mockImplementation(async input => {
    const request = input as Request;
    const call = {
      method: request.method,
      path: decodeURIComponent(new URL(request.url).pathname),
      body: request.method === 'GET' ? '' : await request.text(),
    };
    calls.push(call);
    const reply = handler(call) ?? {
      status: 404,
      body: {error: 'not_found', message: ''},
    };
    return new Response(
      reply.body === undefined ? null : JSON.stringify(reply.body),
      {status: reply.status, headers: {'Content-Type': 'application/json'}},
    );
  });
  return calls;
}

async function render(ui: React.ReactElement) {
  jest.mocked(useAuth).mockReturnValue({
    status: 'signedIn',
    user: {id: ME, firstName: 'Lena', lastName: 'Hennig', roles: ['user']},
  } as unknown as ReturnType<typeof useAuth>);
  const client = new QueryClient({defaultOptions: {queries: {retry: false}}});
  await renderWithProviders(
    <QueryClientProvider client={client}>{ui}</QueryClientProvider>,
  );
}

afterEach(() => {
  jest.restoreAllMocks();
  jest.mocked(router.push).mockClear();
});

describe('list overview (05-01)', () => {
  it('shows cards with count, persons and the next event', async () => {
    mockApi(call =>
      call.path === '/v1/lists'
        ? {
            status: 200,
            body: [
              {
                id: LIST,
                name: TOUR.name,
                eventCount: 2,
                members: TOUR.members,
                nextEvent: TOUR.events[0],
              },
            ],
          }
        : undefined,
    );
    await render(<ListsScreen />);

    expect(await screen.findByText(TOUR.name)).toBeOnTheScreen();
    expect(screen.getByText('2 Feste')).toBeOnTheScreen();
    expect(screen.getByText('3 Personen')).toBeOnTheScreen();
    expect(
      screen.getByText(/Ulmer Weihnachtsmarkt · 23\. Nov/),
    ).toBeOnTheScreen();
    await fireEvent.press(screen.getByTestId(`lists.card.${LIST}`));
    expect(router.push).toHaveBeenCalledWith({
      pathname: '/listen/[id]',
      params: {id: LIST},
    });
  });

  it('creates a list with a friend from the empty state', async () => {
    const calls = mockApi(call => {
      if (call.path === '/v1/lists' && call.method === 'GET') {
        return {status: 200, body: []};
      }
      if (call.path === '/v1/me/friends') {
        return {
          status: 200,
          body: {items: [{...TOUR.members[0], since: '2026-10-01T00:00:00Z'}]},
        };
      }
      if (call.path === '/v1/lists' && call.method === 'POST') {
        return {status: 201, body: {...TOUR, events: []}};
      }
      return undefined;
    });
    await render(<ListsScreen />);

    expect(await screen.findByText('Noch keine Listen')).toBeOnTheScreen();
    await fireEvent.press(screen.getByTestId('lists.empty.new'));
    expect(screen.getByTestId('lists.new.create')).toBeDisabled();
    await fireEvent.changeText(
      screen.getByTestId('lists.new.name'),
      'Sommerfeste 2027',
    );
    await fireEvent.press(
      await screen.findByTestId(`lists.new.friend.${JONAS}`),
    );
    await fireEvent.press(screen.getByTestId('lists.new.create'));

    await waitFor(() =>
      expect(router.push).toHaveBeenCalledWith({
        pathname: '/listen/[id]',
        params: {id: LIST},
      }),
    );
    const post = calls.find(c => c.method === 'POST');
    expect(JSON.parse(post?.body ?? '{}')).toEqual({
      name: 'Sommerfeste 2027',
      memberIds: [JONAS],
    });
    expect(await screen.findByText('Liste erstellt')).toBeOnTheScreen();
  });
});

describe('list detail (05-03, 05-04)', () => {
  function detailApi() {
    return mockApi(call => {
      if (call.path === `/v1/lists/${LIST}` && call.method === 'GET') {
        return {status: 200, body: TOUR};
      }
      if (call.method === 'DELETE' || call.method === 'PATCH') {
        return call.method === 'PATCH'
          ? {status: 200, body: {...TOUR, name: JSON.parse(call.body).name}}
          : {status: 204};
      }
      if (call.path === '/v1/lists') return {status: 200, body: []};
      return undefined;
    });
  }

  it('shows "Du" first and the events chronologically', async () => {
    detailApi();
    await render(<ListDetailScreen listId={LIST} />);

    expect(await screen.findByText(TOUR.name)).toBeOnTheScreen();
    expect(screen.getByText('Mitglieder · 3 Personen')).toBeOnTheScreen();
    const labels = screen
      .getAllByText(/^(Du|Jonas|Mia)$/)
      .map(node => node.props.children);
    expect(labels).toEqual(['Du', 'Jonas', 'Mia']);
    expect(screen.getByText('Ulmer Weihnachtsmarkt')).toBeOnTheScreen();
    expect(screen.queryByTestId('list.delete')).toBeNull();
  });

  it('removes others and events in edit mode, never the own account', async () => {
    const calls = detailApi();
    await render(<ListDetailScreen listId={LIST} />);
    await fireEvent.press(await screen.findByTestId('list.edit'));

    expect(screen.queryByTestId(`list.member.${ME}.remove`)).toBeNull();
    await fireEvent.press(screen.getByTestId(`list.member.${MIA}.remove`));
    await fireEvent.press(screen.getByTestId('list.event.e1.remove'));

    await waitFor(() =>
      expect(screen.queryByTestId(`list.member.${MIA}`)).toBeNull(),
    );
    await waitFor(() =>
      expect(screen.queryByText('Ulmer Weihnachtsmarkt')).toBeNull(),
    );
    expect(calls.map(c => `${c.method} ${c.path}`)).toEqual(
      expect.arrayContaining([
        `DELETE /v1/lists/${LIST}/members/${MIA}`,
        `DELETE /v1/lists/${LIST}/events/e1`,
      ]),
    );
  });

  it('renames with "Fertig" and deletes after confirming', async () => {
    jest
      .spyOn(Alert, 'alert')
      .mockImplementation((_t, _m, buttons?: AlertButton[]) =>
        buttons?.find(b => b.style === 'destructive')?.onPress?.(),
      );
    const calls = detailApi();
    await render(<ListDetailScreen listId={LIST} />);
    await fireEvent.press(await screen.findByTestId('list.edit'));
    await fireEvent.changeText(
      screen.getByTestId('list.name.input'),
      'Advent 2026',
    );
    await fireEvent.press(screen.getByTestId('list.done'));

    expect(await screen.findByText('Advent 2026')).toBeOnTheScreen();
    await fireEvent.press(screen.getByTestId('list.edit'));
    await fireEvent.press(screen.getByTestId('list.delete'));

    expect(await screen.findByText('Liste gelöscht')).toBeOnTheScreen();
    expect(calls.some(c => c.method === 'PATCH')).toBe(true);
    expect(
      calls.some(c => c.method === 'DELETE' && c.path === `/v1/lists/${LIST}`),
    ).toBe(true);
    expect(router.back).toHaveBeenCalled();
  });

  it('explains lists the caller cannot see', async () => {
    mockApi(() => undefined);
    await render(<ListDetailScreen listId={LIST} />);
    expect(
      await screen.findByText('Diese Liste gibt es nicht mehr'),
    ).toBeOnTheScreen();
  });
});
