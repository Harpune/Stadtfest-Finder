/**
 * Map-area helpers for the viewport search: a padded, grid-snapped search area (so small map
 * movements hit the same cached response) and distances computed on the device.
 */
import type {Bbox, GeoPoint} from './filter';

/** Extra area around the viewport that is loaded in advance (share per side). */
export const SEARCH_PADDING = 0.3;
const GRID_STEPS = [0.01, 0.02, 0.05, 0.1, 0.2, 0.5, 1, 2, 5] as const;
const EARTH_RADIUS_KM = 6371.0088;

/**
 * Search area for a viewport: padded by 30 % per side and snapped outward to a grid whose
 * step grows with the area. Panning inside the padding keeps the same area (cache hit).
 */
export function searchArea(viewport: Bbox): Bbox {
  const [w, s, e, n] = viewport;
  const padLon = (e - w) * SEARCH_PADDING;
  const padLat = (n - s) * SEARCH_PADDING;
  const span = Math.max(e - w + 2 * padLon, n - s + 2 * padLat);
  const step: number = GRID_STEPS.find(g => g >= span / 6) ?? 5;
  const snap = (value: number, fn: (x: number) => number) =>
    Math.round(fn(value / step) * step * 1e6) / 1e6;
  return [
    Math.max(-180, snap(w - padLon, Math.floor)),
    Math.max(-90, snap(s - padLat, Math.floor)),
    Math.min(180, snap(e + padLon, Math.ceil)),
    Math.min(90, snap(n + padLat, Math.ceil)),
  ];
}

/** Whether a point lies inside a bbox. */
export function inBbox(point: GeoPoint, [w, s, e, n]: Bbox): boolean {
  return point.lon >= w && point.lon <= e && point.lat >= s && point.lat <= n;
}

/** Great-circle distance in km (spherical approximation, ±0.5 %). */
export function distanceKm(a: GeoPoint, b: GeoPoint): number {
  const toRad = (deg: number) => (deg * Math.PI) / 180;
  const dLat = toRad(b.lat - a.lat);
  const dLon = toRad(b.lon - a.lon);
  const h =
    Math.sin(dLat / 2) ** 2 +
    Math.cos(toRad(a.lat)) * Math.cos(toRad(b.lat)) * Math.sin(dLon / 2) ** 2;
  return 2 * EARTH_RADIUS_KM * Math.asin(Math.sqrt(h));
}

/** Distance rounded to 0.1 km, as shown in cards. */
export function roundedDistanceKm(a: GeoPoint, b: GeoPoint): number {
  return Math.round(distanceKm(a, b) * 10) / 10;
}
