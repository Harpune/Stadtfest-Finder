import {QueryClient, QueryClientProvider} from '@tanstack/react-query';
import {act, fireEvent, screen, waitFor} from '@testing-library/react-native';
import {router} from 'expo-router';
import React from 'react';

import {useAuth} from '@/features/auth/AuthProvider';
import {renderWithProviders} from '@/test-utils';

import {NotificationSettingsScreen} from './NotificationSettingsScreen';
import {NotificationsScreen} from './NotificationsScreen';
import * as push from './push';
import {PushProvider, targetOf} from './PushProvider';
import {AppNotification} from './useNotifications';

jest.mock('@/features/auth/AuthProvider', () => ({useAuth: jest.fn()}));
jest.mock('./push', () => ({
  configureForegroundHandling: jest.fn(),
  isPermissionGranted: jest.fn(async () => true),
  canAskForPermission: jest.fn(async () => false),
  requestPermission: jest.fn(async () => true),
  getPushToken: jest.fn(async () => 'ExponentPushToken[pixel]'),
  devicePlatform: jest.fn(() => 'android'),
  setAppBadge: jest.fn(),
  onPushReceived: jest.fn(() => () => undefined),
  onPushTapped: jest.fn(() => () => undefined),
  takeLaunchPush: jest.fn(() => null),
}));
jest.mock('expo-router', () => {
  const actual = jest.requireActual('expo-router');
  return {...actual, router: {push: jest.fn(), back: jest.fn()}};
});

const NOW = new Date('2026-09-23T16:30:00Z');

function note(
  id: string,
  changes: Partial<AppNotification> = {},
): AppNotification {
  return {
    id,
    type: 'remind',
    text: `Fest ${id} beginnt morgen: 24. Sep 2026 in Aalen.`,
    target: {type: 'event', id: `event-${id}`},
    read: false,
    createdAt: '2026-09-23T16:18:00Z',
    ...changes,
  };
}

interface Call {
  method: string;
  path: string;
  search: string;
  body: string;
}

type Reply = {status: number; body?: unknown; headers?: Record<string, string>};

function mockApi(handler: (call: Call) => Reply | undefined): Call[] {
  const calls: Call[] = [];
  jest.spyOn(global, 'fetch').mockImplementation(async input => {
    const request = input as Request;
    const url = new URL(request.url);
    const call = {
      method: request.method,
      path: decodeURIComponent(url.pathname),
      search: decodeURIComponent(url.search),
      body: request.method === 'GET' ? '' : await request.text(),
    };
    calls.push(call);
    const reply = handler(call) ?? {
      status: 404,
      body: {error: 'not_found', message: ''},
    };
    return new Response(
      reply.body === undefined ? null : JSON.stringify(reply.body),
      {
        status: reply.status,
        headers: {'Content-Type': 'application/json', ...reply.headers},
      },
    );
  });
  return calls;
}

async function render(ui: React.ReactElement) {
  jest
    .mocked(useAuth)
    .mockReturnValue({status: 'signedIn'} as ReturnType<typeof useAuth>);
  const client = new QueryClient({defaultOptions: {queries: {retry: false}}});
  await renderWithProviders(
    <QueryClientProvider client={client}>{ui}</QueryClientProvider>,
  );
}

afterEach(() => {
  jest.restoreAllMocks();
  jest.mocked(router.push).mockClear();
});

describe('notification list (07-01)', () => {
  function listApi(items: AppNotification[], unread: number) {
    return mockApi(call => {
      if (call.path === '/v1/me/notifications' && call.method === 'GET') {
        return {
          status: 200,
          body: {items, nextCursor: null},
          headers: {'X-Unread-Count': String(unread)},
        };
      }
      if (call.method === 'POST' || call.method === 'DELETE') {
        return {status: 204};
      }
      return undefined;
    });
  }

  it('groups new and earlier entries; a tap marks read and opens the event', async () => {
    const calls = listApi(
      [note('a'), note('b', {read: true, type: 'cancel', text: 'Fällt aus.'})],
      1,
    );
    await render(<NotificationsScreen now={NOW} />);

    expect(await screen.findByText('Neu')).toBeOnTheScreen();
    expect(screen.getByText('Früher')).toBeOnTheScreen();
    expect(screen.getByText('Fest abgesagt')).toBeOnTheScreen();
    expect(screen.getAllByText('vor 12 Min.')).toHaveLength(2);
    expect(screen.getByTestId('notifications.item.a.unread')).toBeOnTheScreen();

    await fireEvent.press(screen.getByTestId('notifications.item.a'));

    expect(router.push).toHaveBeenCalledWith({
      pathname: '/f/[id]',
      params: {id: 'event-a'},
    });
    await waitFor(() =>
      expect(calls.map(c => `${c.method} ${c.path}`)).toContain(
        'POST /v1/me/notifications/a/read',
      ),
    );
    await waitFor(() =>
      expect(screen.queryByTestId('notifications.item.a.unread')).toBeNull(),
    );
    // Read entries are not marked again.
    await fireEvent.press(screen.getByTestId('notifications.item.b'));
    expect(calls.filter(c => c.method === 'POST')).toHaveLength(1);
  });

  it('opens the event only once on fast double taps', async () => {
    listApi([note('a')], 1);
    await render(<NotificationsScreen now={NOW} />);

    const row = await screen.findByTestId('notifications.item.a');
    await fireEvent.press(row);
    await fireEvent.press(row);
    await fireEvent.press(row);

    expect(router.push).toHaveBeenCalledTimes(1);
  });

  it('deletes an entry by swipe (accessibility action) and lowers the counter', async () => {
    const calls = listApi([note('a'), note('b', {read: true})], 1);
    calls.length = 0;
    await render(<NotificationsScreen now={NOW} />);

    await fireEvent(
      await screen.findByTestId('notifications.swipe.a.content'),
      'accessibilityAction',
      {nativeEvent: {actionName: 'delete'}},
    );

    await waitFor(() =>
      expect(screen.queryByTestId('notifications.item.a')).toBeNull(),
    );
    expect(screen.getByTestId('notifications.item.b')).toBeOnTheScreen();
    expect(
      calls.some(
        c => c.method === 'DELETE' && c.path === '/v1/me/notifications/a',
      ),
    ).toBe(true);
    expect(
      await screen.findByText('Benachrichtigung gelöscht'),
    ).toBeOnTheScreen();
    expect(screen.queryByTestId('notifications.readAll')).toBeNull();
  });

  it('marks everything read', async () => {
    const calls = listApi([note('a'), note('b')], 2);
    await render(<NotificationsScreen now={NOW} />);

    await fireEvent.press(await screen.findByTestId('notifications.readAll'));

    await waitFor(() =>
      expect(screen.queryByTestId('notifications.readAll')).toBeNull(),
    );
    expect(calls.some(c => c.path === '/v1/me/notifications/read-all')).toBe(
      true,
    );
    expect(screen.queryByText('Neu')).toBeNull();
    expect(screen.getByText('Früher')).toBeOnTheScreen();
  });

  it('shows the empty state', async () => {
    listApi([], 0);
    await render(<NotificationsScreen now={NOW} />);
    expect(
      await screen.findByText('Noch keine Benachrichtigungen'),
    ).toBeOnTheScreen();
  });
});

const DEFAULTS = {
  remind: true,
  remindDaysBefore: 1,
  near: true,
  home: null,
  nearRadiusKm: 25,
  change: true,
  invite: true,
  rsvp: true,
};

describe('notification settings (07-02, 07-03)', () => {
  it('greys out "near" without a home and saves the home without coordinates', async () => {
    const calls = mockApi(call => {
      if (
        call.path === '/v1/me/notification-settings' &&
        call.method === 'GET'
      ) {
        return {status: 200, body: DEFAULTS};
      }
      if (
        call.path === '/v1/me/notification-settings' &&
        call.method === 'PUT'
      ) {
        const body = JSON.parse(call.body) as {home: {postalCode: string}};
        return {
          status: 200,
          body: {
            ...DEFAULTS,
            home: {...body.home, lat: 48.84, lon: 10.09},
          },
        };
      }
      if (call.path === '/v1/geocode') {
        return {
          status: 200,
          body: [
            {
              label: '73430 Aalen',
              city: 'Aalen',
              postalCode: '73430',
              lat: 48.84,
              lon: 10.09,
              kind: 'postcode',
            },
          ],
        };
      }
      if (call.path === '/v1/events/count') {
        return {status: 200, body: {total: 4, byCategory: {}}};
      }
      return undefined;
    });
    await render(<NotificationSettingsScreen />);

    expect(
      await screen.findByText('Lege zuerst deinen Wohnort fest'),
    ).toBeOnTheScreen();
    expect(screen.getByTestId('settings.near')).toBeDisabled();

    await fireEvent.changeText(
      screen.getByTestId('settings.home.input'),
      'Aal',
    );
    await fireEvent.press(
      await screen.findByTestId('settings.home.suggestion.73430'),
    );

    await waitFor(() =>
      expect(screen.getByTestId('settings.preview')).toHaveTextContent(
        /Aktuell 4 Feste im Umkreis von 25 km um Aalen/,
      ),
    );
    const put = calls.find(c => c.method === 'PUT');
    expect(JSON.parse(put?.body ?? '{}').home).toEqual({
      postalCode: '73430',
      placeName: 'Aalen',
    });
    expect(
      screen.getByText(/Mitteilungen sind in den Systemeinstellungen/),
    ).toBeOnTheScreen();
  });

  it('debounces switches into one PUT with the whole object', async () => {
    jest.useFakeTimers();
    const calls = mockApi(call => {
      if (call.path !== '/v1/me/notification-settings') return undefined;
      return call.method === 'GET'
        ? {status: 200, body: DEFAULTS}
        : {status: 200, body: JSON.parse(call.body)};
    });
    await render(<NotificationSettingsScreen />);

    await fireEvent(
      await screen.findByTestId('settings.change'),
      'onValueChange',
      false,
    );
    await fireEvent.press(screen.getByTestId('settings.remind.7'));
    await act(async () => {
      jest.advanceTimersByTime(1000);
    });
    jest.useRealTimers();

    await waitFor(() =>
      expect(calls.filter(c => c.method === 'PUT')).toHaveLength(1),
    );
    const body = JSON.parse(calls.find(c => c.method === 'PUT')?.body ?? '{}');
    expect(body).toMatchObject({remindDaysBefore: 7, home: null});
  });
});

describe('push', () => {
  it('maps push targets to routes', () => {
    expect(targetOf({targetType: 'event', targetId: 'e1'})).toBe('/f/e1');
    expect(
      targetOf({
        type: 'ai_search_completed',
        targetType: 'aiSearch',
        targetId: 'j1',
      }),
    ).toBe('/mod/pruefen/j1');
    expect(
      targetOf({
        type: 'ai_search_failed',
        targetType: 'aiSearch',
        targetId: 'j1',
      }),
    ).toBe('/mod');
    expect(targetOf({})).toBeNull();
  });

  it('registers the device after sign-in and opens a tapped push', async () => {
    const calls = mockApi(call => {
      if (call.path === '/v1/config') {
        return {status: 200, body: {pushProvider: 'expo'}};
      }
      if (call.path === '/v1/me/notifications') {
        return {
          status: 200,
          body: {items: []},
          headers: {'X-Unread-Count': '0'},
        };
      }
      if (call.method === 'POST') return {status: 204};
      return undefined;
    });
    await render(
      <PushProvider>
        <></>
      </PushProvider>,
    );

    await waitFor(() =>
      expect(calls.find(c => c.path === '/v1/me/devices')?.body).toBe(
        JSON.stringify({
          token: 'ExponentPushToken[pixel]',
          platform: 'android',
          provider: 'expo',
        }),
      ),
    );

    const tapped = jest.mocked(push.onPushTapped).mock.calls.at(-1)?.[0];
    await act(async () =>
      tapped?.({
        type: 'cancel',
        notificationId: 'n1',
        targetType: 'event',
        targetId: 'e1',
      }),
    );
    expect(router.push).toHaveBeenCalledWith('/f/e1');
    await waitFor(() =>
      expect(calls.some(c => c.path === '/v1/me/notifications/n1/read')).toBe(
        true,
      ),
    );
  });
});
