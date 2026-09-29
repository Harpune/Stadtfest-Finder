/**
 * Data hooks of the discover screen, built on the generated API hooks (`$api`).
 * Map and list use the same search query, so switching views never reloads.
 */
import {keepPreviousData, useInfiniteQuery} from '@tanstack/react-query';
import {useMemo} from 'react';

import {$api, fetchClient} from '@/api/client';
import type {components} from '@/api/generated/schema';

import type {GeoPoint} from './filter';

export type EventSummary = components['schemas']['EventSummary'];
export type Category = components['schemas']['Category'];
export type EventCount = components['schemas']['EventCount'];
type CountParams = NonNullable<
  import('@/api/generated/schema').operations['countEvents']['parameters']['query']
>;

/** Map shows up to this many markers per viewport (R03 open point: limit 500). */
export const SEARCH_PAGE_SIZE = 500;
const CATEGORIES_STALE_MS = 60 * 60 * 1000;

/** Active categories in moderation order (cached 1 h; the API adds an ETag). */
export function useCategories() {
  return $api.useQuery('get', '/v1/categories', undefined, {
    staleTime: CATEGORIES_STALE_MS,
  });
}

/**
 * Event search for map and list, paged via `cursor` (endless scrolling in the list).
 * Built on TanStack directly: openapi-react-query would send `cursor=0` on the first page.
 */
export function useEventSearch(params: CountParams, enabled = true) {
  const query = useInfiniteQuery({
    queryKey: ['get', '/v1/events', params] as const,
    enabled,
    initialPageParam: null as string | null,
    queryFn: async ({pageParam, signal}) => {
      const cursor = pageParam ? {cursor: pageParam} : {};
      const {data, error} = await fetchClient.GET('/v1/events', {
        params: {query: {...params, limit: SEARCH_PAGE_SIZE, ...cursor}},
        signal,
      });
      if (error) throw error;
      return data;
    },
    getNextPageParam: page => page.nextCursor ?? null,
    // Markers stay on the map until the answer for the new viewport arrives (R03-US2).
    placeholderData: keepPreviousData,
  });
  const items = useMemo<EventSummary[]>(
    () => query.data?.pages.flatMap(page => page.items) ?? [],
    [query.data],
  );
  return {...query, items};
}

/** Result counts (`total`, `byCategory`) for chips, list header and filter preview. */
export function useEventCount(params: CountParams, enabled = true) {
  return $api.useQuery(
    'get',
    '/v1/events/count',
    {params: {query: params}},
    {enabled, placeholderData: keepPreviousData},
  );
}

/**
 * Place name for "vom Standort {Ort}" - once per session (R03-US7). The position is rounded
 * to ~1 km before it leaves the device; the backend rounds again and never stores it.
 */
export function usePlaceName(location: GeoPoint | null) {
  const lat = location ? Math.round(location.lat * 100) / 100 : 0;
  const lon = location ? Math.round(location.lon * 100) / 100 : 0;
  return $api.useQuery(
    'get',
    '/v1/geocode/reverse',
    {params: {query: {lat, lon}}},
    {
      enabled: location !== null,
      staleTime: Infinity,
      gcTime: Infinity,
      retry: false,
    },
  );
}
