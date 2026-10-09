/**
 * Notification settings (R11-US2): every change takes effect at once, the whole object is
 * sent with `PUT`, debounced. On failure the server state returns with a toast.
 */
import {useQuery, useQueryClient} from '@tanstack/react-query';
import {useCallback, useEffect, useRef} from 'react';

import {$api, fetchClient} from '@/api/client';
import type {components} from '@/api/generated/schema';
import {useToast} from '@/components';
import {useAuth} from '@/features/auth/AuthProvider';
import {strings} from '@/strings/de';

export type NotificationSettings =
  components['schemas']['NotificationSettings'];
type SettingsUpdate = components['schemas']['NotificationSettingsUpdate'];

export const SETTINGS_QUERY = $api.queryOptions(
  'get',
  '/v1/me/notification-settings',
);
export const SAVE_DEBOUNCE_MS = 600;

/** The `PUT` body: the home as ZIP code and place name only, never coordinates (E-10). */
export function toUpdate(settings: NotificationSettings): SettingsUpdate {
  const {home, ...rest} = settings;
  return {
    ...rest,
    home: home
      ? {postalCode: home.postalCode, placeName: home.placeName}
      : null,
  };
}

export function useNotificationSettings() {
  const {status} = useAuth();
  const queryClient = useQueryClient();
  const toast = useToast();
  const query = useQuery({...SETTINGS_QUERY, enabled: status === 'signedIn'});
  const timer = useRef<ReturnType<typeof setTimeout> | null>(null);
  const key = SETTINGS_QUERY.queryKey;

  useEffect(
    () => () => {
      if (timer.current) clearTimeout(timer.current);
    },
    [],
  );

  const save = useCallback(
    async (settings: NotificationSettings) => {
      const result = await fetchClient
        .PUT('/v1/me/notification-settings', {body: toUpdate(settings)})
        .catch(() => null);
      if (result?.data) {
        queryClient.setQueryData(key, result.data);
        return true;
      }
      toast(
        result?.error?.error === 'postal_code_unknown'
          ? strings.notificationSettings.postalCodeUnknown
          : strings.notificationSettings.saveFailed,
      );
      void queryClient.invalidateQueries({queryKey: key});
      return false;
    },
    [queryClient, toast, key],
  );

  /** Shows the change at once and saves it after a short pause (or `now`). */
  const change = useCallback(
    (next: NotificationSettings, now = false) => {
      queryClient.setQueryData(key, next);
      if (timer.current) clearTimeout(timer.current);
      if (now) return save(next);
      timer.current = setTimeout(() => void save(next), SAVE_DEBOUNCE_MS);
      return Promise.resolve(true);
    },
    [queryClient, save, key],
  );

  return {settings: query.data, query, change};
}
