/**
 * Loads an event detail. Name and key data from the last list/map result are available at
 * once (R04-US1); the rest arrives with `GET /v1/events/{id}`. A 404 is reported as
 * `notFound` instead of an error (R04-US4).
 */
import {InfiniteData, useQuery, useQueryClient} from '@tanstack/react-query';
import {useMemo} from 'react';

import {fetchClient} from '@/api/client';
import type {components} from '@/api/generated/schema';

import type {EventSummary} from '../discover/useDiscoverData';

export type EventDetail = components['schemas']['EventDetail'];
type EventPage = components['schemas']['EventPage'];

/** Finds an event in any cached search result (map/list share one infinite query). */
function useCachedSummary(eventId: string): EventSummary | undefined {
  const queryClient = useQueryClient();
  return useMemo(() => {
    const cached = queryClient.getQueriesData<InfiniteData<EventPage>>({
      queryKey: ['get', '/v1/events'],
    });
    for (const [, data] of cached) {
      for (const page of data?.pages ?? []) {
        const hit = page.items.find(item => item.id === eventId);
        if (hit) return hit;
      }
    }
    return undefined;
  }, [queryClient, eventId]);
}

export function useEventDetail(eventId: string) {
  const summary = useCachedSummary(eventId);
  const query = useQuery({
    queryKey: ['get', '/v1/events/{eventId}', eventId],
    queryFn: async ({signal}) => {
      const {data, error, response} = await fetchClient.GET(
        '/v1/events/{eventId}',
        {
          params: {path: {eventId}},
          signal,
        },
      );
      if (response.status === 404) return null;
      if (error) throw error;
      return data;
    },
  });
  return {
    summary,
    detail: query.data ?? undefined,
    notFound: query.data === null,
    isLoading: query.isPending,
    isError: query.isError,
    refetch: query.refetch,
  };
}
