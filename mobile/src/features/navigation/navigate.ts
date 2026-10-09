/**
 * Opens a screen once per tap: fast double taps on a row or button would otherwise push the
 * same screen several times before the first one is visible.
 */
import {Href, router} from 'expo-router';

/** Pushes within this time after the last one are ignored (longer than the transition). */
export const PUSH_LOCK_MS = 800;

let lastPush = Number.NEGATIVE_INFINITY;

export function navigate(href: Href, now: number = Date.now()): boolean {
  if (now - lastPush < PUSH_LOCK_MS) return false;
  lastPush = now;
  router.push(href);
  return true;
}

/** For tests: forget the last push. */
export function resetNavigationLock(): void {
  lastPush = Number.NEGATIVE_INFINITY;
}
