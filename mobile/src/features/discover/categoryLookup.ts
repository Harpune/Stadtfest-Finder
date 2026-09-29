import type {Category} from './useDiscoverData';

export interface CategoryLook {
  name: string;
  emoji: string;
  color: string;
}

/** Fallback for events whose category is inactive (no chip, but the event stays visible). */
export const UNKNOWN_CATEGORY: CategoryLook = {
  name: 'Fest',
  emoji: '📍',
  color: '#A89BB8',
};

export function buildCategoryLookup(
  categories: readonly Category[] | undefined,
): (id: string) => CategoryLook {
  const byId = new Map((categories ?? []).map(c => [c.id, c]));
  return id => byId.get(id) ?? UNKNOWN_CATEGORY;
}
