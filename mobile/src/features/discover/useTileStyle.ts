/**
 * Loads the MapTiler style for the color scheme once per day and localizes its labels to
 * German (`localizeStyle`). Returns null while loading, without a key or on failure; the map
 * then uses the offline background style.
 */
import type {StyleSpecification} from '@maplibre/maplibre-react-native';
import {useQuery} from '@tanstack/react-query';

import type {ColorScheme} from '@/theme';

import {localizeStyle} from './localizeStyle';
import {TILE_USER_AGENT, tileStyleUrl} from './mapStyle';

const DAY_MS = 24 * 60 * 60 * 1000;

export function useTileStyle(scheme: ColorScheme): StyleSpecification | null {
  const url = tileStyleUrl(scheme);
  const query = useQuery({
    // The key is part of the URL; keep it out of the query key (devtools, logs).
    queryKey: ['tile-style', scheme],
    enabled: url !== null,
    staleTime: DAY_MS,
    gcTime: DAY_MS,
    retry: 1,
    queryFn: async ({signal}) => {
      const response = await fetch(url as string, {
        headers: {'User-Agent': TILE_USER_AGENT},
        signal,
      });
      if (!response.ok) throw new Error(`Tile style: HTTP ${response.status}`);
      return localizeStyle((await response.json()) as StyleSpecification);
    },
  });
  return query.data ?? null;
}
