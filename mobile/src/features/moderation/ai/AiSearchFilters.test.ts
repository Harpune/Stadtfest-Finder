import {
  activeFilterCount,
  EMPTY_FILTERS,
  periodError,
  toRequestFilters,
} from './AiSearchFilters';

const TODAY = '2026-10-27';

describe('AI search filters (R10c)', () => {
  it('sends nothing without filters', () => {
    expect(activeFilterCount(EMPTY_FILTERS)).toBe(0);
    expect(toRequestFilters(EMPTY_FILTERS)).toBeUndefined();
  });

  it('sends only the filters in use', () => {
    const state = {...EMPTY_FILTERS, dateTo: '2026-12-24', radiusKm: 50};
    expect(activeFilterCount(state)).toBe(2);
    expect(toRequestFilters(state)).toEqual({
      dateTo: '2026-12-24',
      radiusKm: 50,
    });
  });

  it('checks the period like the backend', () => {
    const check = (dateFrom: string | null, dateTo: string | null) =>
      periodError({...EMPTY_FILTERS, dateFrom, dateTo}, TODAY);
    expect(check('2026-11-20', '2026-12-24')).toBeNull();
    expect(check(null, '2027-10-27')).toBeNull();
    expect(check('2026-10-26', null)).toBe(
      'Der Zeitraum darf nicht in der Vergangenheit beginnen.',
    );
    expect(check('2026-12-01', '2026-11-30')).toBe(
      'Das Ende liegt vor dem Beginn.',
    );
    expect(check(null, '2027-10-28')).toBe('Höchstens 12 Monate im Voraus.');
  });
});
