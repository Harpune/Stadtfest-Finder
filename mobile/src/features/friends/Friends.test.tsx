import {QueryClient, QueryClientProvider} from '@tanstack/react-query';
import {fireEvent, screen, waitFor} from '@testing-library/react-native';
import {router} from 'expo-router';
import React from 'react';
import {Alert, AlertButton, Share} from 'react-native';

import {useAuth} from '@/features/auth/AuthProvider';
import {renderWithProviders} from '@/test-utils';
import {themes} from '@/theme';

import {AcceptFriendScreen} from './AcceptFriendScreen';
import {friendColor, friendLinkUrl} from './friends';
import {FriendsScreen} from './FriendsScreen';

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

const TOKEN = 'AbCdEfGhIjKlMnOpQrStUv';
const TIM = {
  id: '11111111-1111-4111-8111-111111111111',
  firstName: 'Tim',
  lastName: 'Krause',
  since: '2026-10-09T12:00:00Z',
};

interface Call {
  method: string;
  path: string;
}

type Reply = {status: number; body?: unknown};

function mockApi(handler: (call: Call) => Reply | undefined): Call[] {
  const calls: Call[] = [];
  jest.spyOn(global, 'fetch').mockImplementation(async input => {
    const request = input as Request;
    const call = {
      method: request.method,
      path: decodeURIComponent(new URL(request.url).pathname),
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

const requestAccountAction = jest.fn(() => false);

async function render(
  ui: React.ReactElement,
  status: 'signedIn' | 'guest' = 'signedIn',
) {
  jest.mocked(useAuth).mockReturnValue({
    status,
    requestAccountAction,
  } as unknown as ReturnType<typeof useAuth>);
  const client = new QueryClient({defaultOptions: {queries: {retry: false}}});
  await renderWithProviders(
    <QueryClientProvider client={client}>{ui}</QueryClientProvider>,
  );
}

function confirmAlerts() {
  jest
    .spyOn(Alert, 'alert')
    .mockImplementation((_t, _m, buttons?: AlertButton[]) =>
      buttons?.find(b => b.style === 'destructive')?.onPress?.(),
    );
}

afterEach(() => {
  jest.restoreAllMocks();
  jest.mocked(router.replace).mockClear();
  requestAccountAction.mockClear();
});

describe('friends list (R12-US3)', () => {
  it('lists friends and removes one on both sides after confirming', async () => {
    confirmAlerts();
    const calls = mockApi(call => {
      if (call.path === '/v1/me/friends')
        return {status: 200, body: {items: [TIM]}};
      if (call.method === 'DELETE') return {status: 204};
      return undefined;
    });
    await render(<FriendsScreen />);

    expect(await screen.findByText('Tim Krause')).toBeOnTheScreen();
    expect(screen.getByText('Befreundet seit Okt 2026')).toBeOnTheScreen();

    await fireEvent(
      screen.getByTestId(`friends.swipe.${TIM.id}.content`),
      'accessibilityAction',
      {nativeEvent: {actionName: 'delete'}},
    );

    await waitFor(() => expect(screen.queryByText('Tim Krause')).toBeNull());
    expect(calls).toContainEqual({
      method: 'DELETE',
      path: `/v1/me/friends/${TIM.id}`,
    });
    expect(await screen.findByText('Tim Krause entfernt')).toBeOnTheScreen();
  });

  it('shows the empty state and the QR code with the share link', async () => {
    const share = jest
      .spyOn(Share, 'share')
      .mockResolvedValue({action: 'sharedAction'});
    mockApi(call => {
      if (call.path === '/v1/me/friends')
        return {status: 200, body: {items: []}};
      if (call.path === '/v1/me/friend-link') {
        return {status: 200, body: {token: TOKEN, createdAt: TIM.since}};
      }
      return undefined;
    });
    await render(<FriendsScreen />);

    expect(await screen.findByText('Noch keine Freunde')).toBeOnTheScreen();
    await fireEvent.press(screen.getByTestId('friends.empty.add'));
    expect(await screen.findByTestId('friends.add.qr')).toBeOnTheScreen();
    await fireEvent.press(screen.getByTestId('friends.add.share'));

    expect(share).toHaveBeenCalledWith({
      message: `Werde mein Freund im Stadtfest-Finder: ${friendLinkUrl(TOKEN)}`,
    });
  });

  it('resets the link after confirming', async () => {
    confirmAlerts();
    const calls = mockApi(call => {
      if (call.path === '/v1/me/friends')
        return {status: 200, body: {items: []}};
      if (call.path === '/v1/me/friend-link') {
        return {status: 200, body: {token: TOKEN, createdAt: TIM.since}};
      }
      if (call.path === '/v1/me/friend-link/rotate') {
        return {
          status: 200,
          body: {token: 'Z'.repeat(22), createdAt: TIM.since},
        };
      }
      return undefined;
    });
    await render(<FriendsScreen />);
    await fireEvent.press(await screen.findByTestId('friends.empty.add'));
    // The button is disabled until the link is loaded.
    await screen.findByTestId('friends.add.qr');
    await fireEvent.press(screen.getByTestId('friends.add.reset'));

    expect(await screen.findByText('Neuer Link erstellt')).toBeOnTheScreen();
    expect(calls.some(c => c.path === '/v1/me/friend-link/rotate')).toBe(true);
  });
});

describe('accepting a friend link (R12-US2)', () => {
  it('shows first name and initial and accepts', async () => {
    const calls = mockApi(call => {
      if (call.path === `/v1/friend-links/${TOKEN}`) {
        return {
          status: 200,
          body: {owner: {firstName: 'Lena', lastNameInitial: 'B'}},
        };
      }
      if (call.path === `/v1/friend-links/${TOKEN}/accept`) {
        return {
          status: 201,
          body: {...TIM, firstName: 'Lena', lastName: 'Beispiel'},
        };
      }
      return undefined;
    });
    await render(<AcceptFriendScreen token={TOKEN} />);

    expect(await screen.findByTestId('friend.accept.text')).toHaveTextContent(
      'Lena B. möchte sich mit dir verbinden.',
    );
    await fireEvent.press(screen.getByTestId('friend.accept.confirm'));

    expect(
      await screen.findByText('Du bist jetzt mit Lena befreundet'),
    ).toBeOnTheScreen();
    expect(calls.some(c => c.method === 'POST')).toBe(true);
    expect(router.replace).toHaveBeenCalledWith('/freunde');
  });

  it('explains reset links', async () => {
    mockApi(() => undefined);
    await render(<AcceptFriendScreen token={TOKEN} />);
    expect(
      await screen.findByText('Dieser Link ist nicht mehr gültig'),
    ).toBeOnTheScreen();
  });

  it('remembers the link for guests and hides the owner', async () => {
    const calls = mockApi(() => undefined);
    await render(<AcceptFriendScreen token={TOKEN} />, 'guest');

    expect(requestAccountAction).toHaveBeenCalledWith({
      type: 'friend',
      token: TOKEN,
    });
    expect(screen.getByTestId('friend.accept.guest')).toBeOnTheScreen();
    expect(calls).toEqual([]);
  });
});

describe('friend helpers', () => {
  it('builds the link and picks a stable color from the palette', () => {
    expect(friendLinkUrl(TOKEN)).toMatch(new RegExp(`/freund/${TOKEN}$`));
    const color = friendColor(TIM.id, themes.dark.colors);
    expect(Object.values(themes.dark.colors.friend)).toContain(color);
    expect(friendColor(TIM.id, themes.dark.colors)).toBe(color);
  });
});
