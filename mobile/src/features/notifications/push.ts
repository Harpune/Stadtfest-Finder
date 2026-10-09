/**
 * Thin wrapper around expo-notifications (R11-US5): permission, push token, listeners.
 * The token type follows `PUSH_PROVIDER` of the backend (`GET /v1/config`): an Expo push
 * token for `expo`, the native APNs/FCM token for `direct`.
 */
import Constants from 'expo-constants';
import * as Notifications from 'expo-notifications';
import {Platform} from 'react-native';

import type {components} from '@/api/generated/schema';

export type PushProviderKind = components['schemas']['PushProvider'];
export type DevicePlatform = components['schemas']['DevicePlatform'];

/** IDs from the push payload (E-04); all values are strings. */
export interface PushData {
  type?: string;
  notificationId?: string;
  targetType?: string;
  targetId?: string;
}

/** In the foreground the app shows its own toast instead of the system banner. */
export function configureForegroundHandling(): void {
  Notifications.setNotificationHandler({
    handleNotification: async () => ({
      shouldShowBanner: false,
      shouldShowList: true,
      shouldPlaySound: false,
      shouldSetBadge: true,
    }),
  });
}

async function ensureAndroidChannel(): Promise<void> {
  // Android 13+ asks for the permission only after a channel exists.
  if (Platform.OS === 'android') {
    await Notifications.setNotificationChannelAsync('default', {
      name: 'Benachrichtigungen',
      importance: Notifications.AndroidImportance.HIGH,
    });
  }
}

export async function isPermissionGranted(): Promise<boolean> {
  return (await Notifications.getPermissionsAsync()).granted;
}

/** Asks for the permission if the system still allows asking; true if granted. */
export async function requestPermission(): Promise<boolean> {
  await ensureAndroidChannel();
  const current = await Notifications.getPermissionsAsync();
  if (current.granted) return true;
  if (!current.canAskAgain) return false;
  return (await Notifications.requestPermissionsAsync()).granted;
}

/** Whether the system dialog can still be shown (otherwise only the system settings help). */
export async function canAskForPermission(): Promise<boolean> {
  const current = await Notifications.getPermissionsAsync();
  return !current.granted && current.canAskAgain;
}

function easProjectId(): string | undefined {
  const extra = Constants.expoConfig?.extra as
    {eas?: {projectId?: string}} | undefined;
  return extra?.eas?.projectId ?? Constants.easConfig?.projectId;
}

/**
 * The push token for the provider, or null if none can be obtained (no permission, no EAS
 * project ID for Expo tokens, no Firebase configuration on Android).
 */
export async function getPushToken(
  provider: PushProviderKind,
): Promise<string | null> {
  if (provider === 'disabled') return null;
  try {
    await ensureAndroidChannel();
    if (provider === 'expo') {
      const projectId = easProjectId();
      if (!projectId) return null;
      return (await Notifications.getExpoPushTokenAsync({projectId})).data;
    }
    const token = await Notifications.getDevicePushTokenAsync();
    return typeof token.data === 'string' ? token.data : null;
  } catch {
    return null;
  }
}

export function devicePlatform(): DevicePlatform {
  return Platform.OS === 'ios' ? 'ios' : 'android';
}

export function setAppBadge(count: number): void {
  Notifications.setBadgeCountAsync(count).catch(() => undefined);
}

function dataOf(notification: Notifications.Notification): PushData {
  const data = notification.request.content.data ?? {};
  const text = (key: string) =>
    typeof data[key] === 'string' ? (data[key] as string) : undefined;
  return {
    type: text('type'),
    notificationId: text('notificationId'),
    targetType: text('targetType'),
    targetId: text('targetId'),
  };
}

/** A push arrived while the app is open. */
export function onPushReceived(
  listener: (title: string, data: PushData) => void,
): () => void {
  const subscription = Notifications.addNotificationReceivedListener(n =>
    listener(n.request.content.title ?? '', dataOf(n)),
  );
  return () => subscription.remove();
}

/** The user tapped a push (app in background or foreground). */
export function onPushTapped(listener: (data: PushData) => void): () => void {
  const subscription = Notifications.addNotificationResponseReceivedListener(
    response => listener(dataOf(response.notification)),
  );
  return () => subscription.remove();
}

/** The push that started the app (cold start), handled once. */
export function takeLaunchPush(): PushData | null {
  const response = Notifications.getLastNotificationResponse();
  if (!response) return null;
  Notifications.clearLastNotificationResponse();
  return dataOf(response.notification);
}
