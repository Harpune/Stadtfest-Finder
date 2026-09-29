import {clusterItems} from './cluster';

const AALEN = {id: 'aalen', lat: 48.8368, lon: 10.0932};
const WASSERALFINGEN = {id: 'wa', lat: 48.8631, lon: 10.105}; // ~3 km away
const ULM = {id: 'ulm', lat: 48.396, lon: 9.99}; // ~50 km away

describe('clusterItems', () => {
  it('groups nearby markers at low zoom and keeps distant ones apart', () => {
    const items = clusterItems([AALEN, WASSERALFINGEN, ULM], 8, null);
    expect(items).toHaveLength(2);
    const cluster = items.find(i => i.kind === 'cluster');
    expect(cluster?.kind === 'cluster' && cluster.items.map(i => i.id)).toEqual(
      ['aalen', 'wa'],
    );
  });

  it('splits clusters when zoomed in', () => {
    const items = clusterItems([AALEN, WASSERALFINGEN, ULM], 13, null);
    expect(items.every(i => i.kind === 'point')).toBe(true);
  });

  it('never puts the selected marker into a cluster', () => {
    const items = clusterItems([AALEN, WASSERALFINGEN, ULM], 8, 'wa');
    expect(items).toHaveLength(3);
    expect(items[items.length - 1]).toEqual({
      kind: 'point',
      item: WASSERALFINGEN,
    });
  });

  it('places the cluster at the centroid of its members', () => {
    const [cluster] = clusterItems([AALEN, WASSERALFINGEN], 6, null);
    expect(cluster?.kind).toBe('cluster');
    if (cluster?.kind === 'cluster') {
      expect(cluster.lat).toBeCloseTo((AALEN.lat + WASSERALFINGEN.lat) / 2);
    }
  });
});
