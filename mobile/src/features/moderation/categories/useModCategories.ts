/**
 * Data access for category maintenance (R09): the list is a TanStack query; changes go
 * through `fetchClient` and refresh the moderation list and the public chips.
 */
import {useQuery, useQueryClient} from '@tanstack/react-query';
import {useCallback} from 'react';

import {$api, fetchClient} from '@/api/client';
import type {components} from '@/api/generated/schema';

export type ModCategory = components['schemas']['ModCategory'];
export type CategoryEmoji = components['schemas']['CategoryEmoji'];
export type CategoryColor = components['schemas']['CategoryColor'];
type ApiError = components['schemas']['Error'];

/** Presets, as in the API enums (design reference §14, theme-farben.md). */
export const CATEGORY_EMOJIS: readonly CategoryEmoji[] = [
  '🎪',
  '🎡',
  '🎄',
  '🐎',
  '🍺',
  '🍷',
  '🎭',
  '🎶',
  '🏰',
  '🎃',
  '🌸',
  '🔥',
];
export const CATEGORY_COLORS: readonly CategoryColor[] = [
  '#FFB547',
  '#FF6B8B',
  '#5EEAD4',
  '#8B9CFF',
  '#7ED957',
  '#C792EA',
];

export const MOD_CATEGORIES_QUERY = $api.queryOptions(
  'get',
  '/v1/mod/categories',
);

export type CategoryResult<T> =
  {ok: true; value: T} | {ok: false; status: number; error?: ApiError};

function result<T>(
  data: T | undefined,
  response: Response | undefined,
  error: ApiError | undefined,
): CategoryResult<T> {
  if (response?.ok && data !== undefined) return {ok: true, value: data};
  return {ok: false, status: response?.status ?? 0, error};
}

export function useModCategories() {
  return useQuery({...MOD_CATEGORIES_QUERY, staleTime: 30_000});
}

export interface CategoryFields {
  name: string;
  emoji: CategoryEmoji;
  color: CategoryColor;
  active: boolean;
}

export const categoryApi = {
  async create(fields: CategoryFields): Promise<CategoryResult<ModCategory>> {
    const r = await fetchClient
      .POST('/v1/mod/categories', {body: {...fields, name: fields.name.trim()}})
      .catch(() => undefined);
    return result(r?.data, r?.response, r?.error);
  },
  async update(
    id: string,
    fields: Partial<CategoryFields>,
  ): Promise<CategoryResult<ModCategory>> {
    const body = fields.name ? {...fields, name: fields.name.trim()} : fields;
    const r = await fetchClient
      .PATCH('/v1/mod/categories/{categoryId}', {
        params: {path: {categoryId: id}},
        body,
      })
      .catch(() => undefined);
    return result(r?.data, r?.response, r?.error);
  },
  async order(ids: string[]): Promise<CategoryResult<ModCategory[]>> {
    const r = await fetchClient
      .PUT('/v1/mod/categories/order', {body: {ids}})
      .catch(() => undefined);
    return result(r?.data, r?.response, r?.error);
  },
  async remove(
    id: string,
    replacementId: string | null,
  ): Promise<CategoryResult<{movedEvents: number}>> {
    const r = await fetchClient
      .DELETE('/v1/mod/categories/{categoryId}', {
        params: {
          path: {categoryId: id},
          query: replacementId ? {replacementId} : {},
        },
      })
      .catch(() => undefined);
    return result(r?.data, r?.response, r?.error);
  },
};

/** After a change: reload the moderation list and the public chips (R09-US5). */
export function useRefreshCategories() {
  const queryClient = useQueryClient();
  return useCallback(
    (categories?: ModCategory[]) => {
      if (categories) {
        queryClient.setQueryData(MOD_CATEGORIES_QUERY.queryKey, categories);
      }
      void queryClient.invalidateQueries({
        queryKey: MOD_CATEGORIES_QUERY.queryKey,
      });
      void queryClient.invalidateQueries({queryKey: ['get', '/v1/categories']});
    },
    [queryClient],
  );
}
