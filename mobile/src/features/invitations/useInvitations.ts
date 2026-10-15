/**
 * Invitations via the API (R14): the own invitation as host, received invitations,
 * answers, reminders and invitation links.
 */
import {useQuery, useQueryClient} from '@tanstack/react-query';
import {useCallback} from 'react';

import {fetchClient} from '@/api/client';
import type {components} from '@/api/generated/schema';
import {useToast} from '@/components';
import {useAuth} from '@/features/auth/AuthProvider';
import {usePush} from '@/features/notifications/PushProvider';
import {strings} from '@/strings/de';

export type HostInvitation = components['schemas']['HostInvitation'];
export type ReceivedInvitation = components['schemas']['ReceivedInvitation'];
export type Invitee = components['schemas']['Invitee'];
export type InvitationPerson = components['schemas']['InvitationPerson'];
export type InviteeStatus = components['schemas']['InviteeStatus'];
export type InvitationLinkPreview =
  components['schemas']['InvitationLinkPreview'];

const s = strings.invitations;

/** Error of an invitation request, mapped to a text by the screens. */
export type InvitationProblem =
  'notFound' | 'notInvitable' | 'self' | 'limited' | 'failed';

export function problemOf(
  status: number | undefined,
  code: string | undefined,
): InvitationProblem {
  if (status === 404) return 'notFound';
  if (code === 'event_not_invitable') return 'notInvitable';
  if (code === 'self_link') return 'self';
  if (status === 429) return 'limited';
  return 'failed';
}

export const PROBLEM_TEXT: Record<InvitationProblem, string> = {
  notFound: s.notFound,
  notInvitable: s.notInvitable,
  self: s.failed,
  limited: s.rateLimited,
  failed: s.failed,
};

export const hostInvitationKey = (eventId: string) =>
  ['get', '/v1/events/{eventId}/invitation', eventId] as const;
export const receivedInvitationKey = (invitationId: string) =>
  ['get', '/v1/me/invitations/{invitationId}', invitationId] as const;
const detailKey = (eventId: string) =>
  ['get', '/v1/events/{eventId}', eventId] as const;

/** The own invitation to an event; `null` while nobody was invited yet (404). */
export function useHostInvitation(eventId: string) {
  const {status} = useAuth();
  return useQuery({
    queryKey: hostInvitationKey(eventId),
    enabled: status === 'signedIn',
    retry: false,
    queryFn: async ({signal}) => {
      const {data, response} = await fetchClient.GET(
        '/v1/events/{eventId}/invitation',
        {params: {path: {eventId}}, signal},
      );
      if (response.status === 404) return null;
      if (!data) throw problemOf(response.status, undefined);
      return data;
    },
  });
}

export function useReceivedInvitation(invitationId: string) {
  const {status} = useAuth();
  return useQuery({
    queryKey: receivedInvitationKey(invitationId),
    enabled: status === 'signedIn',
    retry: false,
    queryFn: async ({signal}) => {
      const {data, error, response} = await fetchClient.GET(
        '/v1/me/invitations/{invitationId}',
        {params: {path: {invitationId}}, signal},
      );
      if (!data) throw problemOf(response.status, error?.error);
      return data;
    },
  });
}

/** Host actions: invite friends, share the link, remind open invitees. */
export function useHostActions(eventId: string) {
  const queryClient = useQueryClient();
  const toast = useToast();
  const {askPermission} = usePush();

  const invite = useCallback(
    async (userIds: string[], message: string) => {
      const trimmed = message.trim();
      const result = await fetchClient
        .POST('/v1/events/{eventId}/invitation/invitees', {
          params: {path: {eventId}},
          body: {userIds, ...(trimmed ? {message: trimmed} : {})},
        })
        .catch(() => null);
      if (!result?.data) {
        toast(
          PROBLEM_TEXT[
            problemOf(result?.response.status, result?.error?.error)
          ],
        );
        return false;
      }
      queryClient.setQueryData(hostInvitationKey(eventId), result.data);
      toast(s.sent(userIds.length));
      // Answers arrive as notifications: ask on the first invitation (R11-US5).
      void askPermission();
      return true;
    },
    [eventId, queryClient, toast, askPermission],
  );

  const linkToken = useCallback(async () => {
    const result = await fetchClient
      .POST('/v1/events/{eventId}/invitation/link', {
        params: {path: {eventId}},
      })
      .catch(() => null);
    if (!result?.data) {
      toast(
        PROBLEM_TEXT[problemOf(result?.response.status, result?.error?.error)],
      );
      return null;
    }
    void queryClient.invalidateQueries({queryKey: hostInvitationKey(eventId)});
    return result.data.token;
  }, [eventId, queryClient, toast]);

  const remind = useCallback(
    async (invitation: HostInvitation) => {
      if (!invitation.invitees.some(i => i.status === 'open')) {
        toast(s.allAnswered);
        return;
      }
      const result = await fetchClient
        .POST('/v1/invitations/{invitationId}/reminders', {
          params: {path: {invitationId: invitation.id}},
        })
        .catch(() => null);
      if (result?.response.status === 429) {
        toast(s.remindLater);
        return;
      }
      if (!result?.data) {
        toast(s.failed);
        return;
      }
      toast(
        result.data.reminded > 0
          ? s.reminded(result.data.reminded)
          : s.allAnswered,
      );
      void queryClient.invalidateQueries({
        queryKey: hostInvitationKey(eventId),
      });
    },
    [eventId, queryClient, toast],
  );

  return {invite, linkToken, remind};
}

/** Answers a received invitation optimistically; accepting also sets the favorite. */
export function useRespond(invitationId: string) {
  const queryClient = useQueryClient();
  const toast = useToast();
  const key = receivedInvitationKey(invitationId);
  return useCallback(
    async (status: InviteeStatus) => {
      await queryClient.cancelQueries({queryKey: key});
      const previous = queryClient.getQueryData<ReceivedInvitation>(key);
      if (previous) queryClient.setQueryData(key, {...previous, status});
      const result = await fetchClient
        .PUT('/v1/invitations/{invitationId}/response', {
          params: {path: {invitationId}},
          body: {status},
        })
        .catch(() => null);
      if (!result?.data) {
        queryClient.setQueryData(key, previous);
        toast(
          PROBLEM_TEXT[
            problemOf(result?.response.status, result?.error?.error)
          ],
        );
        return false;
      }
      queryClient.setQueryData(key, result.data);
      void queryClient.invalidateQueries({
        queryKey: ['get', '/v1/me/favorites'],
      });
      void queryClient.invalidateQueries({
        queryKey: detailKey(result.data.event.id),
      });
      return true;
    },
    [invitationId, queryClient, toast, key],
  );
}
