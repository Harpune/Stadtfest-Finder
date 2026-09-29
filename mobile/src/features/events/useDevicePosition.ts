/**
 * Last known device position if location access was already granted, without asking. Used
 * to show distances on screens other than the map (detail page). Stays on the device.
 */
import * as Location from 'expo-location';
import {useEffect, useState} from 'react';

export interface DevicePosition {
  lat: number;
  lon: number;
}

const MAX_AGE_MS = 10 * 60_000;

export function useDevicePosition(): DevicePosition | null {
  const [position, setPosition] = useState<DevicePosition | null>(null);
  useEffect(() => {
    let active = true;
    (async () => {
      const {granted} = await Location.getForegroundPermissionsAsync();
      if (!granted) return;
      const fix = await Location.getLastKnownPositionAsync({
        maxAge: MAX_AGE_MS,
      });
      if (active && fix)
        setPosition({lat: fix.coords.latitude, lon: fix.coords.longitude});
    })().catch(() => undefined);
    return () => {
      active = false;
    };
  }, []);
  return position;
}
