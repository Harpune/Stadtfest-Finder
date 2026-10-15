import {QueryClient, QueryClientProvider} from '@tanstack/react-query';
import {fireEvent, screen, waitFor} from '@testing-library/react-native';
import {router} from 'expo-router';
import React from 'react';

import {useAuth} from '@/features/auth/AuthProvider';
import {renderWithProviders} from '@/test-utils';

import {HostInvitationScreen} from './HostInvitationScreen';
import {InvitationLinkScreen} from './InvitationLinkScreen';
import {ReceivedInvitationScreen} from './ReceivedInvitationScreen';
import type {HostInvitation, ReceivedInvitation} from './useInvitations';

jest.mock('@/features/auth/AuthProvider', () => ({
  ...jest.requireActual('@/features/auth/AuthProvider'),
  useAuth: jest.fn(),
}));
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
  };
});

const ME = '00000000-0000-4000-8000-000000000001';
const JONAS = '00000000-0000-4000-8000-000000000002';
const MIA = '00000000-0000-4000-8000-000000000003';
const CAN = '00000000-0000-4000-8000-000000000004';
const EVENT_ID = '00000000-0000-4000-8000-0000000000e1';
const INVITATION = '00000000-0000-4000-8000-0000000000a1';
const AT = '2026-10-09T10:00:00Z';

const EVENT = {
  id: EVENT_ID,
  name: 'Stadtfest Schwäbisch Gmünd',
  shortName: 'Stadtfest',
  status: 'published' as const,
  startDate: '2099-10-03',
  endDate: '2099-10-04',
  place: 'Marktplatz',
  city: 'Schwäbisch Gmünd',
  lat: 48.8,
  lon: 9.8,
  categoryId: 'c1',
};

const person = (id: string, firstName: string, lastName: string) => ({
  id,
  firstName,
  lastName,
});

const HOSTED: HostInvitation = {
  id: INVITATION,
  event: EVENT,
  message: 'Treffpunkt 19:30 am Marktplatz',
  invitees: [
    {
      person: person(JONAS, 'Jonas', 'Weber'),
      status: 'accepted',
      invitedAt: AT,
    },
    {person: person(MIA, 'Mia', 'Schulz'), status: 'declined', invitedAt: AT},
    {person: person(CAN, 'Can', 'Yilmaz'), status: 'open', invitedAt: AT},
  ],
};

const RECEIVED: ReceivedInvitation = {
  id: INVITATION,
  event: EVENT,
  host: person(JONAS, 'Jonas', 'Weber'),
  message: 'Samstagabend zur Coverband-Nacht?',
  createdAt: AT,
  status: 'open',
  others: [
    {person: person(MIA, 'Mia', 'Schulz'), status: 'accepted', invitedAt: AT},
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

async function render(ui: React.ReactElement, status = 'signedIn') {
  jest.mocked(useAuth).mockReturnValue({
    status,
    user: {id: ME, firstName: 'Lena', lastName: 'Hennig', roles: ['user']},
    requestAccountAction: jest.fn(() => status === 'signedIn'),
  } as unknown as ReturnType<typeof useAuth>);
  const client = new QueryClient({defaultOptions: {queries: {retry: false}}});
  await renderWithProviders(
    <QueryClientProvider client={client}>{ui}</QueryClientProvider>,
  );
}

afterEach(() => {
  jest.restoreAllMocks();
  jest.mocked(router.push).mockClear();
  jest.mocked(router.replace).mockClear();
});

describe('compose (06-02)', () => {
  it('sends to the selected friends and switches to the overview', async () => {
    const calls = mockApi(call => {
      if (call.path === `/v1/events/${EVENT_ID}/invitation`) return undefined;
      if (call.path === '/v1/me/friends') {
        return {
          status: 200,
          body: {
            items: [
              {...person(JONAS, 'Jonas', 'Weber'), since: AT},
              {...person(MIA, 'Mia', 'Schulz'), since: AT},
            ],
          },
        };
      }
      if (call.path.endsWith('/invitation/invitees')) {
        return {
          status: 201,
          body: {
            ...HOSTED,
            invitees: [HOSTED.invitees[0]!],
            message: 'Kommst du?',
          },
        };
      }
      return undefined;
    });
    await render(<HostInvitationScreen eventId={EVENT_ID} />);

    expect(await screen.findByText('Freunde einladen')).toBeOnTheScreen();
    await screen.findByTestId(`invitation.friend.${JONAS}`);
    expect(screen.getByTestId('invitation.compose.send')).toBeDisabled();
    await fireEvent.press(screen.getByTestId(`invitation.friend.${JONAS}`));
    expect(screen.getByText('Einladung senden (1)')).toBeOnTheScreen();
    await fireEvent.changeText(
      screen.getByTestId('invitation.compose.message'),
      '  Kommst du?  ',
    );
    await fireEvent.press(screen.getByTestId('invitation.compose.send'));

    expect(await screen.findByTestId('invitation.counts')).toBeOnTheScreen();
    expect(await screen.findByText('1 Einladung verschickt')).toBeOnTheScreen();
    const post = calls.find(c => c.method === 'POST');
    expect(JSON.parse(post?.body ?? '{}')).toEqual({
      userIds: [JONAS],
      message: 'Kommst du?',
    });
  });
});

describe('overview (06-01)', () => {
  it('counts the host as coming and groups the invitees', async () => {
    const calls = mockApi(call => {
      if (call.path === `/v1/events/${EVENT_ID}/invitation`) {
        return {status: 200, body: HOSTED};
      }
      if (call.path.endsWith('/reminders')) {
        return {status: 202, body: {reminded: 1}};
      }
      return undefined;
    });
    await render(<HostInvitationScreen eventId={EVENT_ID} />);

    expect(await screen.findByLabelText('2 kommen')).toBeOnTheScreen();
    expect(screen.getByLabelText('1 offen')).toBeOnTheScreen();
    expect(screen.getByLabelText('1 abgesagt')).toBeOnTheScreen();
    expect(
      screen.getByText('„Treffpunkt 19:30 am Marktplatz“'),
    ).toBeOnTheScreen();
    expect(screen.getByText('Noch keine Antwort')).toBeOnTheScreen();
    expect(
      screen.getByTestId(`invitation.invitee.${MIA}.status`),
    ).toHaveTextContent('Abgesagt');

    await fireEvent.press(screen.getByTestId('invitation.remind'));
    expect(
      await screen.findByText('Erinnerung an 1 Person verschickt'),
    ).toBeOnTheScreen();
    expect(calls.some(c => c.path.endsWith('/reminders'))).toBe(true);
  });

  it('explains the 24 hour reminder limit', async () => {
    mockApi(call => {
      if (call.path === `/v1/events/${EVENT_ID}/invitation`) {
        return {status: 200, body: HOSTED};
      }
      if (call.path.endsWith('/reminders')) {
        return {status: 429, body: {error: 'reminded_recently', message: ''}};
      }
      return undefined;
    });
    await render(<HostInvitationScreen eventId={EVENT_ID} />);
    await fireEvent.press(await screen.findByTestId('invitation.remind'));
    expect(
      await screen.findByText('Du kannst erst morgen wieder erinnern'),
    ).toBeOnTheScreen();
  });
});

describe('received invitation (06-03, 06-04)', () => {
  it('accepts, shows the banner and resets with "Ändern"', async () => {
    const calls = mockApi(call => {
      if (call.path === `/v1/me/invitations/${INVITATION}`) {
        return {status: 200, body: RECEIVED};
      }
      if (call.method === 'PUT') {
        return {
          status: 200,
          body: {...RECEIVED, status: JSON.parse(call.body).status},
        };
      }
      return undefined;
    });
    await render(<ReceivedInvitationScreen invitationId={INVITATION} />);

    expect(
      await screen.findByText('Jonas Weber lädt dich ein'),
    ).toBeOnTheScreen();
    expect(
      screen.getByTestId(`received.other.${MIA}.status`),
    ).toHaveTextContent('Zugesagt');
    await fireEvent.press(screen.getByTestId('received.accept'));
    expect(await screen.findByText('✓ Du hast zugesagt')).toBeOnTheScreen();
    expect(screen.queryByTestId('received.accept')).toBeNull();

    await fireEvent.press(screen.getByTestId('received.banner.change'));
    expect(await screen.findByTestId('received.accept')).toBeOnTheScreen();
    expect(calls.filter(c => c.method === 'PUT').map(c => c.body)).toEqual([
      JSON.stringify({status: 'accepted'}),
      JSON.stringify({status: 'open'}),
    ]);
  });

  it('shows a declined answer', async () => {
    mockApi(call =>
      call.path === `/v1/me/invitations/${INVITATION}`
        ? {status: 200, body: {...RECEIVED, status: 'declined'}}
        : undefined,
    );
    await render(<ReceivedInvitationScreen invitationId={INVITATION} />);
    expect(await screen.findByText('Du hast abgesagt')).toBeOnTheScreen();
  });

  it('explains invitations the caller cannot see', async () => {
    mockApi(() => undefined);
    await render(<ReceivedInvitationScreen invitationId={INVITATION} />);
    expect(
      await screen.findByText('Diese Einladung gibt es nicht mehr'),
    ).toBeOnTheScreen();
  });
});

describe('invitation link (R14-US3)', () => {
  const TOKEN = 'A'.repeat(22);

  it('accepts and opens the received invitation', async () => {
    mockApi(call => {
      if (call.path === `/v1/invitation-links/${TOKEN}`) {
        return {
          status: 200,
          body: {
            host: {firstName: 'Jonas', lastNameInitial: 'W'},
            event: EVENT,
            own: false,
          },
        };
      }
      if (call.path.endsWith('/accept')) return {status: 201, body: RECEIVED};
      return undefined;
    });
    await render(<InvitationLinkScreen token={TOKEN} />);
    expect(await screen.findByText('Jonas W. lädt dich ein')).toBeOnTheScreen();
    await fireEvent.press(screen.getByTestId('invitationLink.accept'));
    await waitFor(() =>
      expect(router.replace).toHaveBeenCalledWith({
        pathname: '/einladung/[id]',
        params: {id: INVITATION},
      }),
    );
  });

  it('sends the host of the own link to the overview', async () => {
    mockApi(call =>
      call.path === `/v1/invitation-links/${TOKEN}`
        ? {
            status: 200,
            body: {
              host: {firstName: 'Lena', lastNameInitial: 'H'},
              event: EVENT,
              own: true,
            },
          }
        : undefined,
    );
    await render(<InvitationLinkScreen token={TOKEN} />);
    await waitFor(() =>
      expect(router.replace).toHaveBeenCalledWith({
        pathname: '/einladen/[eventId]',
        params: {eventId: EVENT_ID},
      }),
    );
  });

  it('remembers the link for guests', async () => {
    mockApi(() => undefined);
    await render(<InvitationLinkScreen token={TOKEN} />, 'guest');
    expect(screen.getByTestId('invitationLink.guest')).toBeOnTheScreen();
    expect(jest.mocked(useAuth)().requestAccountAction).toHaveBeenCalledWith({
      type: 'invitationLink',
      token: TOKEN,
    });
  });
});
