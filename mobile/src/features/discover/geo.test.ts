import {distanceKm, inBbox, roundedDistanceKm, searchArea} from './geo';

describe('searchArea', () => {
  const viewport: [number, number, number, number] = [10.0, 48.8, 10.2, 48.9];

  it('covers the viewport with padding on every side', () => {
    const [w, s, e, n] = searchArea(viewport);
    expect(w).toBeLessThanOrEqual(10.0 - 0.06);
    expect(s).toBeLessThanOrEqual(48.8 - 0.03);
    expect(e).toBeGreaterThanOrEqual(10.2 + 0.06);
    expect(n).toBeGreaterThanOrEqual(48.9 + 0.03);
  });

  it('keeps the same area for small pans (cache hits)', () => {
    const moved: [number, number, number, number] = [
      10.004, 48.803, 10.204, 48.903,
    ];
    expect(searchArea(moved)).toEqual(searchArea(viewport));
  });

  it('uses a coarser grid when zoomed out', () => {
    const germany = searchArea([5.8, 47.2, 15.1, 55.1]);
    expect(germany.every(v => Number.isInteger(v * 2))).toBe(true);
  });
});

describe('distances', () => {
  const aalen = {lat: 48.8375, lon: 10.0933};
  const ulm = {lat: 48.3984, lon: 9.9916};

  it('computes the great-circle distance', () => {
    expect(distanceKm(aalen, ulm)).toBeCloseTo(49.4, 0);
    expect(roundedDistanceKm(aalen, aalen)).toBe(0);
  });

  it('checks bbox containment', () => {
    expect(inBbox(aalen, [10, 48.8, 10.2, 48.9])).toBe(true);
    expect(inBbox(ulm, [10, 48.8, 10.2, 48.9])).toBe(false);
  });
});
