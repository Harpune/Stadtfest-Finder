import {
  activeFilterCount,
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

  it('counts the time filter and each category', () => {
    expect(activeFilterCount(f({time: 'today'}))).toBe(1);
    expect(activeFilterCount(f({categoryIds: ['a', 'b']}))).toBe(2);
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
  it('sends nothing for the default filter without area', () => {
    expect(toQueryParams(DEFAULT_FILTER, undefined, '')).toEqual({});
  });

  it('maps time, months, categories, text and the map area; never a position', () => {
    const params = toQueryParams(
      f({
        time: 'months',
        months: ['2026-12', '2026-11'],
        categoryIds: ['c2', 'c1'],
      }),
      [9.123456, 48.123456, 10.987654, 49.987654],
      '  Aalen ',
    );
    expect(params).toEqual({
      when: 'months',
      months: ['2026-11', '2026-12'],
      categories: ['c1', 'c2'],
      q: 'Aalen',
      bbox: [9.1235, 48.1235, 10.9877, 49.9877],
    });
    expect(params).not.toHaveProperty('lat');
    expect(params).not.toHaveProperty('radiusKm');
  });

  it('ignores search text shorter than 2 characters and empty month selections', () => {
    expect(toQueryParams(f({time: 'months'}), undefined, 'a')).toEqual({});
  });
});

describe('toggleValue', () => {
  it('adds and removes values', () => {
    expect(toggleValue(['a'], 'b')).toEqual(['a', 'b']);
    expect(toggleValue(['a', 'b'], 'a')).toEqual(['b']);
  });
});
