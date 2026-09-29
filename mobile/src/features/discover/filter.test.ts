import {
  activeFilterCount,
  clampRadius,
  DEFAULT_FILTER,
  DiscoverFilter,
  monthOptions,
  pruneCategories,
  pruneMonths,
  toggleValue,
  toQueryParams,
} from './filter';

const f = (patch: Partial<DiscoverFilter>): DiscoverFilter => ({
  ...DEFAULT_FILTER,
  ...patch,
});

describe('activeFilterCount', () => {
  it('is 0 for the default filter', () => {
    expect(activeFilterCount(DEFAULT_FILTER)).toBe(0);
  });

  it('counts time, each category and a changed radius', () => {
    expect(activeFilterCount(f({time: 'today'}))).toBe(1);
    expect(activeFilterCount(f({categoryIds: ['a', 'b']}))).toBe(2);
    expect(activeFilterCount(f({categoryIds: ['a'], radiusKm: 10}))).toBe(2); // screen 01-07
  });

  it('does not count "Zeitraum wählen" without months', () => {
    expect(activeFilterCount(f({time: 'months', months: []}))).toBe(0);
    expect(activeFilterCount(f({time: 'months', months: ['2026-11']}))).toBe(1);
  });
});

describe('pruneCategories', () => {
  it('silently drops categories that are no longer active', () => {
    expect(
      pruneCategories(f({categoryIds: ['a', 'gone']}), ['a', 'b']).categoryIds,
    ).toEqual(['a']);
  });

  it('returns the same object when nothing changes', () => {
    const filter = f({categoryIds: ['a']});
    expect(pruneCategories(filter, ['a'])).toBe(filter);
  });
});

describe('monthOptions', () => {
  it('lists 12 months from the current one with the year on next-year months', () => {
    const options = monthOptions('2026-10-15');
    expect(options).toHaveLength(12);
    expect(options[0]).toEqual({value: '2026-10', label: 'Okt'});
    expect(options[3]).toEqual({value: '2027-01', label: 'Jan 27'});
    expect(options[11]).toEqual({value: '2027-09', label: 'Sep 27'});
  });

  it('drops selected months that are in the past', () => {
    const filter = f({time: 'months', months: ['2026-09', '2026-10']});
    expect(pruneMonths(filter, '2026-10-01').months).toEqual(['2026-10']);
  });
});

describe('toQueryParams', () => {
  it('maps the default filter to radius only', () => {
    expect(toQueryParams(DEFAULT_FILTER, {}, '')).toEqual({radiusKm: 150});
  });

  it('maps time, months, categories, text and area with rounding', () => {
    const params = toQueryParams(
      f({
        time: 'months',
        months: ['2026-12', '2026-11'],
        categoryIds: ['c2', 'c1'],
      }),
      {
        bbox: [9.12345, 48.12345, 10.98765, 49.98765],
        reference: {lat: 48.83712, lon: 10.09341},
      },
      '  Aalen ',
    );
    expect(params).toEqual({
      radiusKm: 150,
      when: 'months',
      months: ['2026-11', '2026-12'],
      categories: ['c1', 'c2'],
      q: 'Aalen',
      bbox: [9.123, 48.123, 10.988, 49.988],
      lat: 48.84,
      lon: 10.09,
    });
  });

  it('ignores search text shorter than 2 characters and empty month selections', () => {
    expect(toQueryParams(f({time: 'months'}), {}, 'a')).toEqual({
      radiusKm: 150,
    });
  });
});

describe('helpers', () => {
  it('toggles values and clamps the radius to 10 km steps', () => {
    expect(toggleValue(['a'], 'b')).toEqual(['a', 'b']);
    expect(toggleValue(['a', 'b'], 'a')).toEqual(['b']);
    expect(clampRadius(4)).toBe(10);
    expect(clampRadius(147)).toBe(150);
    expect(clampRadius(999)).toBe(300);
  });
});
