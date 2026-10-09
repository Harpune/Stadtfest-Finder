/**
 * Shared lists via the API (R13). Member and event changes are single operations and
 * optimistic, so two members editing at the same time do not overwrite each other.
 */
import {useQuery, useQueryClient} from '@tanstack/react-query';
import {useCallback} from 'react';

import {$api, fetchClient} from '@/api/client';
import type {components} from '@/api/generated/schema';
import {useToast} from '@/components';
import {useAuth} from '@/features/auth/AuthProvider';
import {strings} from '@/strings/de';

export type SharedList = components['schemas']['SharedList'];
export type SharedListSummary = components['schemas']['SharedListSummary'];
export type ListMember = components['schemas']['ListMember'];
export type ListEvent = components['schemas']['ListEvent'];

export const LISTS_QUERY = $api.queryOptions('get', '/v1/lists');

export function listQuery(listId: string) {
  return $api.queryOptions('get', '/v1/lists/{listId}', {
    params: {path: {listId}},
  });
}

export function useLists() {
  const {status} = useAuth();
  return useQuery({...LISTS_QUERY, enabled: status === 'signedIn'});
}

export function useList(listId: string) {
  const {status} = useAuth();
  return useQuery({
    ...listQuery(listId),
    enabled: status === 'signedIn',
    retry: false,
  });
}

/** Create, rename, delete and the single member/event operations. */
export function useListActions(listId: string) {
  const queryClient = useQueryClient();
  const toast = useToast();
  const key = listQuery(listId).queryKey;

  const refreshOverview = useCallback(
    () => queryClient.invalidateQueries({queryKey: LISTS_QUERY.queryKey}),
    [queryClient],
  );

  /** Applies `change` to the cached list at once and runs `request`; rolls back on failure. */
  const optimistic = useCallback(
    async (
      change: (list: SharedList) => SharedList,
      request: () => Promise<{response: Response} | null>,
    ) => {
      await queryClient.cancelQueries({queryKey: key});
      const previous = queryClient.getQueryData<SharedList>(key);
      if (previous) queryClient.setQueryData<SharedList>(key, change(previous));
      const result = await request().catch(() => null);
      if (!result?.response.ok) {
        queryClient.setQueryData(key, previous);
        toast(strings.lists.failed);
        return false;
      }
      void refreshOverview();
      return true;
    },
    [queryClient, toast, key, refreshOverview],
  );

  const path = {params: {path: {listId}}};

  return {
    rename: (name: string) =>
      optimistic(
        list => ({...list, name}),
        () => fetchClient.PATCH('/v1/lists/{listId}', {...path, body: {name}}),
      ),
    remove: async () => {
      const result = await fetchClient
        .DELETE('/v1/lists/{listId}', path)
        .catch(() => null);
      if (!result?.response.ok) {
        toast(strings.lists.failed);
        return false;
      }
      queryClient.removeQueries({queryKey: key});
      void refreshOverview();
      return true;
    },
    addMember: (member: ListMember) =>
      optimistic(
        list => ({...list, members: [...list.members, member]}),
        () =>
          fetchClient.POST('/v1/lists/{listId}/members', {
            ...path,
            body: {userId: member.id},
          }),
      ),
    removeMember: (userId: string) =>
      optimistic(
        list => ({...list, members: list.members.filter(m => m.id !== userId)}),
        () =>
          fetchClient.DELETE('/v1/lists/{listId}/members/{userId}', {
            params: {path: {listId, userId}},
          }),
      ),
    addEvent: (event: ListEvent) =>
      optimistic(
        list => ({
          ...list,
          events: [...list.events, event].sort((a, b) =>
            a.startDate.localeCompare(b.startDate),
          ),
        }),
        () =>
          fetchClient.PUT('/v1/lists/{listId}/events/{eventId}', {
            params: {path: {listId, eventId: event.id}},
          }),
      ),
    removeEvent: (eventId: string) =>
      optimistic(
        list => ({...list, events: list.events.filter(e => e.id !== eventId)}),
        () =>
          fetchClient.DELETE('/v1/lists/{listId}/events/{eventId}', {
            params: {path: {listId, eventId}},
          }),
      ),
  };
}

/** Creates a list; returns its ID or null (toast on failure). */
export function useCreateList() {
  const queryClient = useQueryClient();
  const toast = useToast();
  return useCallback(
    async (name: string, memberIds: string[]) => {
      const {data} = await fetchClient
        .POST('/v1/lists', {body: {name, memberIds}})
        .catch(() => ({data: undefined}));
      if (!data) {
        toast(strings.lists.failed);
        return null;
      }
      queryClient.setQueryData(listQuery(data.id).queryKey, data);
      void queryClient.invalidateQueries({queryKey: LISTS_QUERY.queryKey});
      toast(strings.lists.created);
      return data.id;
    },
    [queryClient, toast],
  );
}
