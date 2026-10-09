/**
 * Favorites of the signed-in user (R06-US1, US2). One query feeds the timeline, the hearts
 * on list and detail, so a change anywhere shows up everywhere without reloading.
 */
import {useQuery, useQueryClient} from '@tanstack/react-query';
import {useCallback, useMemo} from 'react';

import {$api, fetchClient} from '@/api/client';
import type {components} from '@/api/generated/schema';
import {useToast} from '@/components';
import {useAuth} from '@/features/auth/AuthProvider';
import {usePush} from '@/features/notifications/PushProvider';
import {strings} from '@/strings/de';

import type {FavoriteEntry} from './timeline';

type EventSummary = components['schemas']['EventSummary'];
type FavoriteList = components['schemas']['FavoriteList'];

/** Past favorites are loaded right away; the drawer only shows them on request. */
export const FAVORITES_QUERY = $api.queryOptions('get', '/v1/me/favorites', {
  params: {query: {include: 'past'}},
});

/** The favorites of the signed-in user; disabled for guests. */
export function useFavorites() {
  const {status} = useAuth();
  return useQuery({...FAVORITES_QUERY, enabled: status === 'signedIn'});
}

/** IDs of all favorite events (empty for guests and while loading). */
export function useFavoriteIds(): ReadonlySet<string> {
  const {data} = useFavorites();
  return useMemo(
    () => new Set((data?.items ?? []).map(item => item.id)),
    [data],
  );
}

/** Builds the timeline entry for an optimistic update from what the screen already shows. */
export function favoriteEntryFrom(
  event: EventSummary,
  category: {name: string; emoji: string},
): FavoriteEntry {
  return {
    ...event,
    categoryName: category.name,
    emoji: category.emoji,
    favoritedAt: new Date().toISOString(),
  };
}

/**
 * Toggles a favorite optimistically: the heart and the timeline change at once, a toast
 * confirms, and on failure the previous state is restored with "Das hat nicht geklappt".
 */
export function useToggleFavorite() {
  const queryClient = useQueryClient();
  const toast = useToast();
  const {askPermission} = usePush();
  const key = FAVORITES_QUERY.queryKey;

  return useCallback(
    async (entry: FavoriteEntry, favorite: boolean) => {
      await queryClient.cancelQueries({queryKey: key});
      const previous = queryClient.getQueryData<FavoriteList>(key);
      const others = (previous?.items ?? []).filter(i => i.id !== entry.id);
      queryClient.setQueryData<FavoriteList>(key, {
        items: favorite ? [...others, entry] : others,
      });
      const params = {params: {path: {eventId: entry.id}}};
      const result = await (
        favorite
          ? fetchClient.PUT('/v1/me/favorites/{eventId}', params)
          : fetchClient.DELETE('/v1/me/favorites/{eventId}', params)
      ).catch(() => null);
      if (!result?.response.ok) {
        queryClient.setQueryData(key, previous);
        toast(strings.favorites.failed);
        return;
      }
      toast(favorite ? strings.favorites.added : strings.favorites.removed);
      // Server order and `favoritedAt` replace the optimistic entry.
      void queryClient.invalidateQueries({queryKey: key});
      // The system asks for notifications on the first favorite, not at app start
      // (R11-US5); afterwards the call returns without a dialog.
      if (favorite) void askPermission();
    },
    [queryClient, toast, key, askPermission],
  );
}
