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
 * Place name of the map center for the list header "um {Ort}" (R03-US4). The center is
 * rounded to ~1 km; the backend rounds again and never stores it.
 */
export function useAreaName(center: GeoPoint | null, enabled: boolean) {
  const lat = center ? Math.round(center.lat * 100) / 100 : 0;
  const lon = center ? Math.round(center.lon * 100) / 100 : 0;
  return $api.useQuery(
    'get',
    '/v1/geocode/reverse',
    {params: {query: {lat, lon}}},
    {
      enabled: enabled && center !== null,
      staleTime: Infinity,
      retry: false,
      placeholderData: keepPreviousData,
    },
  );
}

export type Place = components['schemas']['GeocodeResult'];

/**
 * First city or ZIP code matching the search text, for "Zu {Ort} springen" (R03-US5).
 * Street addresses are not offered.
 */
export function usePlaceSuggestion(query: string) {
  const q = query.trim();
  const result = $api.useQuery(
    'get',
    '/v1/geocode',
    {params: {query: {q, limit: 3}}},
    {enabled: q.length >= 2, staleTime: 5 * 60_000, retry: false},
  );
  return q.length >= 2
    ? result.data?.find(place => place.kind !== 'address')
    : undefined;
}
