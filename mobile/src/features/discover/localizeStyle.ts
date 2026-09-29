/**
 * Map label language: MapTiler's default styles label places with `name:en`. This rewrites
 * all text-field expressions to German (`name:de`), falling back to the local `name`.
 */
import type {StyleSpecification} from '@maplibre/maplibre-react-native';

const FOREIGN_NAME_FIELDS = ['name:en', 'name:latin', 'name_en', 'name_int'];

type Json = unknown;

function localizeExpression(value: Json, language: string): Json {
  const field = `name:${language}`;
  if (typeof value === 'string') {
    // Token strings such as "{name:en}" or "{name:en}\n{ref}".
    return FOREIGN_NAME_FIELDS.some(f => value === `{${f}}`)
      ? ['coalesce', ['get', field], ['get', 'name']]
      : value;
  }
  if (!Array.isArray(value)) return value;
  if (
    value.length === 2 &&
    value[0] === 'get' &&
    typeof value[1] === 'string' &&
    FOREIGN_NAME_FIELDS.includes(value[1])
  ) {
    return ['coalesce', ['get', field], ['get', 'name']];
  }
  return value.map(item => localizeExpression(item, language));
}

/** Returns a copy of the style with all labels in `language` (default German). */
export function localizeStyle(
  style: StyleSpecification,
  language = 'de',
): StyleSpecification {
  return {
    ...style,
    layers: style.layers.map(layer => {
      if (layer.type !== 'symbol' || !layer.layout?.['text-field'])
        return layer;
      return {
        ...layer,
        layout: {
          ...layer.layout,
          'text-field': localizeExpression(
            layer.layout['text-field'],
            language,
          ) as (typeof layer.layout)['text-field'],
        },
      };
    }),
  };
}

/**
 * Removes sources without data (`url`, `tiles`, `data` or `urls`) that no layer uses.
 * MapTiler ships `maptiler_attribution` only to carry the attribution text; MapLibre Native
 * warns "source must have tiles" for it. The attribution is rendered as visible text instead.
 */
export function dropEmptySources(
  style: StyleSpecification,
): StyleSpecification {
  const used = new Set(
    style.layers
      .map(layer => ('source' in layer ? layer.source : undefined))
      .filter(Boolean),
  );
  const sources = Object.fromEntries(
    Object.entries(style.sources).filter(([name, source]) => {
      const hasData = ['url', 'tiles', 'data', 'urls'].some(
        key => key in source,
      );
      return hasData || used.has(name);
    }),
  );
  return {...style, sources};
}
