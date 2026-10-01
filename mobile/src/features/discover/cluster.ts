/**
 * Client-side marker clustering (R03-US2): markers closer than 46 px on screen are grouped.
 * The selected event is never part of a cluster. Projection: Web Mercator with 512 px tiles
 * (MapLibre), so pixel distances match the rendered map at the given zoom.
 */

export const CLUSTER_RADIUS_PX = 46;
const TILE_SIZE = 512;

export interface ClusterInput {
  id: string;
  lat: number;
  lon: number;
}

export type MapItem<T extends ClusterInput> =
  | {kind: 'point'; item: T}
  | {kind: 'cluster'; key: string; lat: number; lon: number; items: T[]};

function project(lat: number, lon: number, zoom: number): [number, number] {
  const scale = TILE_SIZE * 2 ** zoom;
  const x = ((lon + 180) / 360) * scale;
  const sin = Math.sin((lat * Math.PI) / 180);
  const y = (0.5 - Math.log((1 + sin) / (1 - sin)) / (4 * Math.PI)) * scale;
  return [x, y];
}

/**
 * Greedy distance clustering in screen space.
 *
 * @param items Events with coordinates, in the API order (stable input => stable output).
 * @param zoom Current map zoom.
 * @param selectedId Selected event, always returned as a single point.
 */
export function clusterItems<T extends ClusterInput>(
  items: readonly T[],
  zoom: number,
  selectedId: string | null,
  radiusPx = CLUSTER_RADIUS_PX,
): MapItem<T>[] {
  const result: MapItem<T>[] = [];
  const candidates = items.filter(item => item.id !== selectedId);
  const projected = candidates.map(item => project(item.lat, item.lon, zoom));
  const used = new Array<boolean>(candidates.length).fill(false);
  const radiusSq = radiusPx * radiusPx;

  candidates.forEach((item, i) => {
    if (used[i]) return;
    used[i] = true;
    const [x, y] = projected[i] ?? [0, 0];
    const members = [item];
    for (let j = i + 1; j < candidates.length; j++) {
      if (used[j]) continue;
      const [xj, yj] = projected[j] ?? [0, 0];
      if ((xj - x) ** 2 + (yj - y) ** 2 < radiusSq) {
        used[j] = true;
        members.push(candidates[j] as T);
      }
    }
    if (members.length === 1) {
      result.push({kind: 'point', item});
    } else {
      const lat = members.reduce((sum, m) => sum + m.lat, 0) / members.length;
      const lon = members.reduce((sum, m) => sum + m.lon, 0) / members.length;
      result.push({
        kind: 'cluster',
        key: `c:${item.id}`,
        lat,
        lon,
        items: members,
      });
    }
  });

  const selected = items.find(item => item.id === selectedId);
  if (selected) result.push({kind: 'point', item: selected});
  return result;
}

/**
 * Whether zooming in up to `maxZoom` splits a cluster. False for festivals at (almost) the
 * same spot, e.g. two events on one market square: those are offered as a list instead.
 */
export function separatesByZoom<T extends ClusterInput>(
  items: readonly T[],
  maxZoom: number,
): boolean {
  return clusterItems(items, maxZoom, null).length > 1;
}
