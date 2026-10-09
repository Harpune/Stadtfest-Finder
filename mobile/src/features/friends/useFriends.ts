/** Friends list and own friend link via the API (R12). */
import {useQuery, useQueryClient} from '@tanstack/react-query';
import {useCallback} from 'react';

import {$api, fetchClient} from '@/api/client';
import type {components} from '@/api/generated/schema';
import {useToast} from '@/components';
import {useAuth} from '@/features/auth/AuthProvider';
import {strings} from '@/strings/de';

import {displayName} from './friends';

export type Friend = components['schemas']['Friend'];
type FriendList = components['schemas']['FriendList'];

export const FRIENDS_QUERY = $api.queryOptions('get', '/v1/me/friends');
export const FRIEND_LINK_QUERY = $api.queryOptions('get', '/v1/me/friend-link');

export function useFriends() {
  const {status} = useAuth();
  return useQuery({...FRIENDS_QUERY, enabled: status === 'signedIn'});
}

export function useFriendLink(enabled: boolean) {
  const {status} = useAuth();
  return useQuery({
    ...FRIEND_LINK_QUERY,
    enabled: enabled && status === 'signedIn',
  });
}

/** Resets the link; the old QR code stops working. */
export function useRotateFriendLink() {
  const queryClient = useQueryClient();
  const toast = useToast();
  return useCallback(async () => {
    const {data} = await fetchClient
      .POST('/v1/me/friend-link/rotate')
      .catch(() => ({data: undefined}));
    if (!data) {
      toast(strings.friends.failed);
      return;
    }
    queryClient.setQueryData(FRIEND_LINK_QUERY.queryKey, data);
    toast(strings.friends.resetDone);
  }, [queryClient, toast]);
}

/** Removes a friend optimistically; both sides lose the friendship. */
export function useRemoveFriend() {
  const queryClient = useQueryClient();
  const toast = useToast();
  const key = FRIENDS_QUERY.queryKey;
  return useCallback(
    async (friend: Friend) => {
      await queryClient.cancelQueries({queryKey: key});
      const previous = queryClient.getQueryData<FriendList>(key);
      if (previous) {
        queryClient.setQueryData<FriendList>(key, {
          items: previous.items.filter(item => item.id !== friend.id),
        });
      }
      const result = await fetchClient
        .DELETE('/v1/me/friends/{userId}', {
          params: {path: {userId: friend.id}},
        })
        .catch(() => null);
      if (!result?.response.ok) {
        queryClient.setQueryData(key, previous);
        toast(strings.friends.failed);
        return;
      }
      toast(
        strings.friends.removed(displayName(friend.firstName, friend.lastName)),
      );
    },
    [queryClient, toast, key],
  );
}
