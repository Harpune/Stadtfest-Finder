/**
 * Map style source (ADR 0009): MapTiler Cloud vector styles per color scheme. Without a key
 * (local dev, tests, Storybook) an offline style with only the background color is used, so
 * no external service is contacted.
 */
import type {StyleSpecification} from '@maplibre/maplibre-react-native';

import type {ColorScheme} from '@/theme';

const KEY = process.env.EXPO_PUBLIC_MAPTILER_KEY ?? '';
const STYLE_IDS: Record<ColorScheme, string> = {
  dark: process.env.EXPO_PUBLIC_MAPTILER_STYLE_DARK || 'streets-v2-dark',
  light: process.env.EXPO_PUBLIC_MAPTILER_STYLE_LIGHT || 'streets-v2',
};

export const HAS_TILE_KEY = KEY.length > 0;

export function offlineStyle(background: string): StyleSpecification {
  return {
    version: 8,
    sources: {},
    layers: [
      {
        id: 'background',
        type: 'background',
        paint: {'background-color': background},
      },
    ],
  };
}

export function mapStyleFor(
  scheme: ColorScheme,
  background: string,
): string | StyleSpecification {
  if (!HAS_TILE_KEY) return offlineStyle(background);
  const style = encodeURIComponent(STYLE_IDS[scheme]);
  return `https://api.maptiler.com/maps/${style}/style.json?key=${encodeURIComponent(KEY)}`;
}
