/**
 * Discover filters (R03-US6/US7): model, defaults, active-filter count, month grid and the
 * mapping to the query parameters of `GET /v1/events` and `/v1/events/count`.
 */
import type {operations} from '@/api/generated/schema';

import {IsoDate, monthShort, parseIsoDate} from '../events/dates';

export type TimeKind = 'all' | 'today' | 'weekend' | 'months';

export interface DiscoverFilter {
  time: TimeKind;
  /** Selected months `YYYY-MM`; only used for `time === 'months'`. */
  months: string[];
  categoryIds: string[];
  radiusKm: number;
}

export const MIN_RADIUS_KM = 10;
export const MAX_RADIUS_KM = 300;
export const RADIUS_STEP_KM = 10;
export const DEFAULT_RADIUS_KM = 150;
export const MONTH_GRID_SIZE = 12;

export const DEFAULT_FILTER: DiscoverFilter = {
  time: 'all',
  months: [],
  categoryIds: [],
  radiusKm: DEFAULT_RADIUS_KM,
};

/** "Zeitraum wählen" without a month behaves like "Alle Termine". */
export function effectiveTime(filter: DiscoverFilter): TimeKind {
  return filter.time === 'months' && filter.months.length === 0
    ? 'all'
    : filter.time;
}

/** Badge count on the filter button: time (1) + each category + radius (1). */
export function activeFilterCount(filter: DiscoverFilter): number {
  return (
    (effectiveTime(filter) !== 'all' ? 1 : 0) +
    filter.categoryIds.length +
    (filter.radiusKm !== DEFAULT_RADIUS_KM ? 1 : 0)
  );
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

export function clampRadius(km: number): number {
  const stepped = Math.round(km / RADIUS_STEP_KM) * RADIUS_STEP_KM;
  return Math.min(MAX_RADIUS_KM, Math.max(MIN_RADIUS_KM, stepped));
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

/** Where to search: map viewport plus the distance reference (location or map center). */
export interface SearchArea {
  bbox?: Bbox;
  reference?: GeoPoint;
}

type CountQuery = NonNullable<operations['countEvents']['parameters']['query']>;

const round = (value: number, decimals: number) =>
  Math.round(value * 10 ** decimals) / 10 ** decimals;

/**
 * Query parameters shared by search and count. Coordinates are rounded (bbox ~100 m,
 * reference ~1 km) so small map movements hit the same cache entry and exact positions are
 * never sent.
 */
export function toQueryParams(
  filter: DiscoverFilter,
  area: SearchArea,
  query: string,
): CountQuery {
  const params: CountQuery = {radiusKm: filter.radiusKm};
  const time = effectiveTime(filter);
  if (time !== 'all') params.when = time;
  if (time === 'months') params.months = [...filter.months].sort();
  if (filter.categoryIds.length > 0)
    params.categories = [...filter.categoryIds].sort();
  const text = query.trim();
  if (text.length >= 2) params.q = text;
  if (area.bbox) params.bbox = area.bbox.map(v => round(v, 3));
  if (area.reference) {
    params.lat = round(area.reference.lat, 2);
    params.lon = round(area.reference.lon, 2);
  }
  return params;
}
