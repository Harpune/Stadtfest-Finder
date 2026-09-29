import type {StyleSpecification} from '@maplibre/maplibre-react-native';

import {dropEmptySources, localizeStyle} from './localizeStyle';

const GERMAN = ['coalesce', ['get', 'name:de'], ['get', 'name']];

function styleWith(textFields: unknown[]): StyleSpecification {
  return {
    version: 8,
    sources: {},
    layers: [
      {id: 'bg', type: 'background'},
      ...textFields.map((field, i) => ({
        id: `l${i}`,
        type: 'symbol' as const,
        source: 'maptiler',
        layout: {'text-field': field},
      })),
    ],
  } as StyleSpecification;
}

function fields(style: StyleSpecification): unknown[] {
  return style.layers
    .filter(l => l.type === 'symbol')
    .map(l => (l.layout as Record<string, unknown>)['text-field']);
}

describe('localizeStyle', () => {
  it('rewrites English names to German with the local name as fallback', () => {
    const style = styleWith([
      '{name:en}',
      ['coalesce', ['get', 'name:en'], ['get', 'name']],
      ['concat', ['get', 'name:latin'], '\n', ['get', 'name:nonlatin']],
    ]);
    expect(fields(localizeStyle(style))).toEqual([
      GERMAN,
      ['coalesce', GERMAN, ['get', 'name']],
      ['concat', GERMAN, '\n', ['get', 'name:nonlatin']],
    ]);
  });

  it('keeps labels that are not names', () => {
    const style = styleWith(['{ref}', '{housenumber}', '{name}']);
    expect(fields(localizeStyle(style))).toEqual([
      '{ref}',
      '{housenumber}',
      '{name}',
    ]);
  });

  it('does not mutate the input style', () => {
    const style = styleWith(['{name:en}']);
    localizeStyle(style);
    expect(fields(style)).toEqual(['{name:en}']);
  });
});

describe('dropEmptySources', () => {
  it('removes unused sources without data and keeps the rest', () => {
    const style = {
      version: 8,
      sources: {
        maptiler_planet: {
          type: 'vector',
          url: 'https://api.maptiler.com/tiles/v3/tiles.json',
        },
        maptiler_attribution: {type: 'vector', attribution: '© MapTiler'},
      },
      layers: [
        {
          id: 'water',
          type: 'fill',
          source: 'maptiler_planet',
          'source-layer': 'water',
        },
      ],
    } as unknown as StyleSpecification;
    expect(Object.keys(dropEmptySources(style).sources)).toEqual([
      'maptiler_planet',
    ]);
  });
});
