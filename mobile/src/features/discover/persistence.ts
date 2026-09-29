/**
 * Small local persistence for the discover screen (AsyncStorage):
 * - the last map camera, used as start view when location access is denied (R03-US1),
 * - the last loaded search result for offline reading (R03-US8).
 * Neither contains the user's position: the camera is only stored without location access.
 */
import AsyncStorage from '@react-native-async-storage/async-storage';

import type {EventSummary} from './useDiscoverData';

const CAMERA_KEY = 'discover.camera.v1';
const LAST_SEARCH_KEY = 'discover.lastSearch.v1';

export interface StoredCamera {
  center: [lon: number, lat: number];
  zoom: number;
}

export interface StoredSearch {
  savedAt: string; // ISO timestamp
  items: EventSummary[];
}

async function readJson<T>(key: string): Promise<T | null> {
  try {
    const raw = await AsyncStorage.getItem(key);
    return raw ? (JSON.parse(raw) as T) : null;
  } catch {
    return null;
  }
}

async function writeJson(key: string, value: unknown): Promise<void> {
  try {
    await AsyncStorage.setItem(key, JSON.stringify(value));
  } catch {
    // Persistence is a convenience; failures must not break the screen.
  }
}

export const loadCamera = () => readJson<StoredCamera>(CAMERA_KEY);

export function saveCamera(camera: StoredCamera): Promise<void> {
  const round = (v: number) => Math.round(v * 100) / 100;
  return writeJson(CAMERA_KEY, {
    center: [round(camera.center[0]), round(camera.center[1])],
    zoom: Math.round(camera.zoom * 10) / 10,
  });
}

export const loadLastSearch = () => readJson<StoredSearch>(LAST_SEARCH_KEY);

export function saveLastSearch(
  items: EventSummary[],
  now = new Date(),
): Promise<void> {
  return writeJson(LAST_SEARCH_KEY, {savedAt: now.toISOString(), items});
}
