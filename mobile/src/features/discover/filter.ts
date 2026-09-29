/**
 * Discover filters (R03-US6/US7): model, defaults, active-filter count, month grid and the
 * mapping to the query parameters of `GET /v1/events` and `/v1/events/count`.
 *
 * There is no radius: the visible map area (viewport) is the only spatial restriction. The
 * user narrows the area by zooming (decision 29.09.2026).
 */
import type {operations} from '@/api/generated/schema';

import {IsoDate, monthShort, parseIsoDate} from '../events/dates';

export type TimeKind = 'all' | 'today' | 'weekend' | 'months';

export interface DiscoverFilter {
  time: TimeKind;
  /** Selected months `YYYY-MM`; only used for `time === 'months'`. */
  months: string[];
  categoryIds: string[];
}

export const MONTH_GRID_SIZE = 12;

export const DEFAULT_FILTER: DiscoverFilter = {
  time: 'all',
  months: [],
  categoryIds: [],
};

/** "Zeitraum wählen" without a month behaves like "Alle Termine". */
export function effectiveTime(filter: DiscoverFilter): TimeKind {
  return filter.time === 'months' && filter.months.length === 0
    ? 'all'
    : filter.time;
}

/** Badge count on the filter button: time (1) + each category. */
export function activeFilterCount(filter: DiscoverFilter): number {
  return (effectiveTime(filter) !== 'all' ? 1 : 0) + filter.categoryIds.length;
}

export function toggleValue(values: string[], value: string): string[] {
  return values.includes(value)
    ? values.filter(v => v !== value)
    : [...values, value];
}

/**
 * Drops categories that are no longer active (R03-US6). Returns the same object if nothing
 * changed, so callers can skip state updates.
 */
export function pruneCategories(
  filter: DiscoverFilter,
  activeCategoryIds: readonly string[],
): DiscoverFilter {
  const kept = filter.categoryIds.filter(id => activeCategoryIds.includes(id));
  return kept.length === filter.categoryIds.length
    ? filter
    : {...filter, categoryIds: kept};
}

export interface MonthOption {
  value: string; // YYYY-MM
  /** "Okt"; months of the next year carry the year: "Jan 27". */
  label: string;
}

/** The next 12 months starting with the current one (E-03: month grid). */
export function monthOptions(
  today: IsoDate,
  count = MONTH_GRID_SIZE,
): MonthOption[] {
  const {year, month} = parseIsoDate(today);
  return Array.from({length: count}, (_, i) => {
    const index = month - 1 + i;
    const y = year + Math.floor(index / 12);
    const m = (index % 12) + 1;
    const short = monthShort(m);
    return {
      value: `${y}-${String(m).padStart(2, '0')}`,
      label: y === year ? short : `${short} ${String(y).slice(-2)}`,
    };
  });
}

/** Drops months that lie before the current month (e.g. after midnight on the 1st). */
export function pruneMonths(
  filter: DiscoverFilter,
  today: IsoDate,
): DiscoverFilter {
  const valid = new Set(monthOptions(today).map(o => o.value));
  const kept = filter.months.filter(m => valid.has(m));
  return kept.length === filter.months.length
    ? filter
    : {...filter, months: kept};
}

export type Bbox = [
  minLon: number,
  minLat: number,
  maxLon: number,
  maxLat: number,
];

export interface GeoPoint {
  lat: number;
  lon: number;
}

type CountQuery = NonNullable<operations['countEvents']['parameters']['query']>;

const round = (value: number, decimals: number) =>
  Math.round(value * 10 ** decimals) / 10 ** decimals;

/**
 * Query parameters shared by search and count: filters and the map area. No position is
 * sent; distances are computed on the device (`geo.ts`).
 */
export function toQueryParams(
  filter: DiscoverFilter,
  bbox: Bbox | undefined,
  query: string,
): CountQuery {
  const params: CountQuery = {};
  const time = effectiveTime(filter);
  if (time !== 'all') params.when = time;
  if (time === 'months') params.months = [...filter.months].sort();
  if (filter.categoryIds.length > 0) {
    params.categories = [...filter.categoryIds].sort();
  }
  const text = query.trim();
  if (text.length >= 2) params.q = text;
  if (bbox) params.bbox = bbox.map(v => round(v, 4));
  return params;
}
