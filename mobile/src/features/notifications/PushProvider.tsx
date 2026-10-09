/**
 * Push in the app (R11-US5):
 * - registers the device after the permission and after every sign-in,
 * - asks for the permission on the first favorite, not at app start,
 * - in the foreground shows a toast and refreshes the counter,
 * - a tap on a push opens its target (also on a cold start) and marks it read.
 */
import {useQuery} from '@tanstack/react-query';
import React, {
  createContext,
  PropsWithChildren,
  useCallback,
  useContext,
  useEffect,
  useMemo,
  useRef,
} from 'react';

import {navigate} from '@/features/navigation/navigate';
import {$api} from '@/api/client';
import {useToast} from '@/components';
import {useAuth} from '@/features/auth/AuthProvider';

import {registerDevice} from './devices';
import {
  configureForegroundHandling,
  isPermissionGranted,
  onPushReceived,
  onPushTapped,
  PushData,
  PushProviderKind,
  requestPermission,
  setAppBadge,
  takeLaunchPush,
} from './push';
import {
  useMarkRead,
  useRefreshNotifications,
  useUnreadCount,
} from './useNotifications';

export const CONFIG_QUERY = $api.queryOptions('get', '/v1/config');

interface PushContextValue {
  /** Push delivery of the backend; `disabled` until the configuration is loaded. */
  provider: PushProviderKind;
  /** Asks for the permission (first favorite, settings) and registers the device. */
  askPermission: () => Promise<boolean>;
}

const PushContext = createContext<PushContextValue>({
  provider: 'disabled',
  askPermission: async () => false,
});

/** Where a tapped push leads: event detail, or the AI search of the moderator. */
export function targetOf(data: PushData): string | null {
  if (!data.targetId) return null;
  switch (data.targetType) {
    case 'event':
      return `/f/${data.targetId}`;
    case 'friend':
      return '/freunde';
    case 'list':
      return `/listen/${data.targetId}`;
    case 'invitation':
      return `/einladung/${data.targetId}`;
    case 'invitationOverview':
      return `/einladen/${data.targetId}`;
    case 'aiSearch':
      return data.type === 'ai_search_completed'
        ? `/mod/pruefen/${data.targetId}`
        : '/mod';
    default:
      return null;
  }
}

export function PushProvider({children}: PropsWithChildren) {
  const {status} = useAuth();
  const toast = useToast();
  const refresh = useRefreshNotifications();
  const markRead = useMarkRead();
  const unread = useUnreadCount();
  const signedIn = status === 'signedIn';
  const config = useQuery({...CONFIG_QUERY, staleTime: Infinity});
  const provider: PushProviderKind = config.data?.pushProvider ?? 'disabled';
  const launchHandled = useRef(false);
  const lastOpened = useRef<{key: string; at: number} | null>(null);

  useEffect(() => configureForegroundHandling(), []);

  // After every sign-in (and app start while signed in): register if already allowed.
  useEffect(() => {
    if (!signedIn || provider === 'disabled') return;
    void isPermissionGranted()
      .then(granted => (granted ? registerDevice(provider) : false))
      .catch(() => false);
  }, [signedIn, provider]);

  const askPermission = useCallback(async () => {
    if (provider === 'disabled') return false;
    const granted = await requestPermission().catch(() => false);
    if (granted && signedIn) await registerDevice(provider);
    return granted;
  }, [provider, signedIn]);

  const open = useCallback(
    (data: PushData) => {
      // A cold start may report the same tap via the listener and the launch response.
      const key = `${data.notificationId ?? ''}:${data.targetId ?? ''}`;
      const now = Date.now();
      if (
        lastOpened.current?.key === key &&
        now - lastOpened.current.at < 3000
      ) {
        return;
      }
      lastOpened.current = {key, at: now};
      if (data.notificationId) void markRead(data.notificationId);
      const target = targetOf(data);
      if (target) navigate(target as never);
    },
    [markRead],
  );

  useEffect(
    () =>
      onPushReceived(title => {
        if (title) toast(title);
        void refresh();
      }),
    [toast, refresh],
  );

  useEffect(() => onPushTapped(open), [open]);

  // Cold start from a push: open its target once the session is restored.
  useEffect(() => {
    if (status === 'restoring' || launchHandled.current) return;
    launchHandled.current = true;
    const data = takeLaunchPush();
    if (data) open(data);
  }, [status, open]);

  useEffect(() => setAppBadge(unread), [unread]);

  const value = useMemo(
    () => ({provider, askPermission}),
    [provider, askPermission],
  );
  return <PushContext.Provider value={value}>{children}</PushContext.Provider>;
}

export function usePush(): PushContextValue {
  return useContext(PushContext);
}
