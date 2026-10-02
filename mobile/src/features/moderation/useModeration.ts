/**
 * Data access of the moderation view (R07). Lists and details are TanStack queries; changes
 * go through `fetchClient` and refresh the overview afterwards.
 */
import {useQuery, useQueryClient} from '@tanstack/react-query';
import {router} from 'expo-router';
import {useCallback} from 'react';

import {$api, fetchClient} from '@/api/client';
import type {components} from '@/api/generated/schema';
import {useToast} from '@/components';
import {strings} from '@/strings/de';

import type {ModEventCreate, ModEventDetail, ModEventPatch} from './form';

export type ModEventSummary = components['schemas']['ModEventSummary'];
type ApiError = components['schemas']['Error'];

export const MOD_EVENTS_QUERY = $api.queryOptions('get', '/v1/mod/events');

const detailKey = (eventId: string) =>
  ['get', '/v1/mod/events/{eventId}', eventId] as const;

/** Result of a change: the stored event, or the HTTP status with the error body. */
export type ModResult =
  | {ok: true; event: ModEventDetail}
  | {ok: false; status: number; error?: ApiError};

function toResult(
  response: Response | undefined,
  data: ModEventDetail | undefined,
  error: ApiError | undefined,
): ModResult {
  if (response?.ok && data) return {ok: true, event: data};
  return {ok: false, status: response?.status ?? 0, error};
}

export function useModEvents() {
  return useQuery(MOD_EVENTS_QUERY);
}

export function useModEvent(eventId: string | null) {
  return useQuery({
    queryKey: detailKey(eventId ?? ''),
    enabled: eventId !== null,
    queryFn: async ({signal}) => {
      const {data, error, response} = await fetchClient.GET(
        '/v1/mod/events/{eventId}',
        {params: {path: {eventId: eventId ?? ''}}, signal},
      );
      if (error)
        throw Object.assign(new Error(error.error), {status: response.status});
      return data;
    },
  });
}

const path = (eventId: string) => ({params: {path: {eventId}}});

/** API calls of the form; network errors become status 0. */
export const modApi = {
  async create(body: ModEventCreate): Promise<ModResult> {
    const result = await fetchClient
      .POST('/v1/mod/events', {body})
      .catch(() => undefined);
    return toResult(result?.response, result?.data, result?.error);
  },
  async update(
    eventId: string,
    body: ModEventPatch,
    version: number,
  ): Promise<ModResult> {
    const result = await fetchClient
      .PATCH('/v1/mod/events/{eventId}', {
        params: {path: {eventId}, header: {'If-Match': `"${version}"`}},
        body,
        headers: {'Content-Type': 'application/merge-patch+json'},
      })
      .catch(() => undefined);
    return toResult(result?.response, result?.data, result?.error);
  },
  async publish(eventId: string): Promise<ModResult> {
    const result = await fetchClient
      .POST('/v1/mod/events/{eventId}/publish', path(eventId))
      .catch(() => undefined);
    return toResult(result?.response, result?.data, result?.error);
  },
  async unpublish(eventId: string): Promise<ModResult> {
    const result = await fetchClient
      .POST('/v1/mod/events/{eventId}/unpublish', path(eventId))
      .catch(() => undefined);
    return toResult(result?.response, result?.data, result?.error);
  },
  async cancel(eventId: string, reason: string): Promise<ModResult> {
    const result = await fetchClient
      .POST('/v1/mod/events/{eventId}/cancel', {
        ...path(eventId),
        body: {reason: reason.trim() || null},
      })
      .catch(() => undefined);
    return toResult(result?.response, result?.data, result?.error);
  },
  async remove(eventId: string): Promise<{ok: boolean; status: number}> {
    const result = await fetchClient
      .DELETE('/v1/mod/events/{eventId}', path(eventId))
      .catch(() => undefined);
    return {
      ok: result?.response.ok ?? false,
      status: result?.response.status ?? 0,
    };
  },
};

/**
 * Leaves the moderation view: back to the map, which reloads because published or
 * withdrawn events change what users see (R07-US1).
 */
export function useExitModeration() {
  const queryClient = useQueryClient();
  const toast = useToast();
  return useCallback(
    (message: string = strings.mod.exited) => {
      void queryClient.invalidateQueries({queryKey: ['get', '/v1/events']});
      void queryClient.invalidateQueries({
        queryKey: ['get', '/v1/events/count'],
      });
      // Category changes show up as chips at once (R09-US5).
      void queryClient.invalidateQueries({queryKey: ['get', '/v1/categories']});
      queryClient.removeQueries({queryKey: ['get', '/v1/mod/events']});
      // Back to the map in the root stack; dismissAll() would only pop the nested
      // moderation stack (form → overview).
      router.dismissTo('/');
      toast(message);
    },
    [queryClient, toast],
  );
}

/** Refreshes the overview and the stored detail after a change. */
export function useRefreshModeration() {
  const queryClient = useQueryClient();
  return useCallback(
    (event?: ModEventDetail) => {
      if (event) queryClient.setQueryData(detailKey(event.id), event);
      void queryClient.invalidateQueries({queryKey: MOD_EVENTS_QUERY.queryKey});
    },
    [queryClient],
  );
}
