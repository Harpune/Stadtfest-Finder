/**
 * Location permission and current position (R03-US1). The position stays on the device:
 * it is only sent (rounded) as a query parameter and never persisted.
 *
 * A GPS fix can take long (indoors, cold start); callers must not block on it. `locating`
 * is true while the first fix is pending after permission was granted.
 */
import * as Location from 'expo-location';
import {useCallback, useEffect, useState} from 'react';

import type {GeoPoint} from './filter';

export type LocationState =
  | {status: 'pending'}
  | {status: 'denied'}
  | {status: 'granted'; position: GeoPoint | null; locating: boolean};

/** Upper bound for one position request. */
export const POSITION_TIMEOUT_MS = 10_000;

function withTimeout<T>(promise: Promise<T>, ms: number): Promise<T | null> {
  return Promise.race([
    promise,
    new Promise<null>(resolve => setTimeout(() => resolve(null), ms)),
  ]);
}

export function useUserLocation() {
  const [state, setState] = useState<LocationState>({status: 'pending'});

  const locate = useCallback(async (): Promise<GeoPoint | null> => {
    setState(s =>
      s.status === 'granted'
        ? {...s, locating: true}
        : {status: 'granted', position: null, locating: true},
    );
    let position: GeoPoint | null = null;
    try {
      const fix =
        (await Location.getLastKnownPositionAsync({maxAge: 5 * 60_000})) ??
        (await withTimeout(
          Location.getCurrentPositionAsync({
            accuracy: Location.Accuracy.Balanced,
          }),
          POSITION_TIMEOUT_MS,
        ));
      if (fix) position = {lat: fix.coords.latitude, lon: fix.coords.longitude};
    } catch {
      position = null;
    }
    setState(s => ({
      status: 'granted',
      position: position ?? (s.status === 'granted' ? s.position : null),
      locating: false,
    }));
    return position;
  }, []);

  useEffect(() => {
    let active = true;
    (async () => {
      // The system shows its dialog only once; later calls return the stored decision.
      const {granted} = await Location.requestForegroundPermissionsAsync();
      if (!active) return;
      if (!granted) {
        setState({status: 'denied'});
        return;
      }
      await locate();
    })().catch(() => active && setState({status: 'denied'}));
    return () => {
      active = false;
    };
  }, [locate]);

  return {location: state, locate};
}
