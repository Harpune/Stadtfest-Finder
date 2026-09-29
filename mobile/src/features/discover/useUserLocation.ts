/**
 * Location permission and current position (R03-US1). The position stays on the device:
 * it is only sent (rounded) as a query parameter and never persisted.
 */
import * as Location from 'expo-location';
import {useCallback, useEffect, useState} from 'react';

import type {GeoPoint} from './filter';

export type LocationState =
  | {status: 'pending'}
  | {status: 'denied'}
  | {status: 'granted'; position: GeoPoint | null};

export function useUserLocation() {
  const [state, setState] = useState<LocationState>({status: 'pending'});

  const locate = useCallback(async (): Promise<GeoPoint | null> => {
    try {
      const last = await Location.getLastKnownPositionAsync({
        maxAge: 5 * 60_000,
      });
      const fix =
        last ??
        (await Location.getCurrentPositionAsync({
          accuracy: Location.Accuracy.Balanced,
        }));
      const position = {lat: fix.coords.latitude, lon: fix.coords.longitude};
      setState({status: 'granted', position});
      return position;
    } catch {
      setState({status: 'granted', position: null});
      return null;
    }
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
