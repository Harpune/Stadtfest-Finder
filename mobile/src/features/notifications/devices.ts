/**
 * Registration of this device's push token at the backend (R11-US5): after the permission
 * and after every sign-in; removed again on sign-out.
 */
import {fetchClient} from '@/api/client';

import {devicePlatform, getPushToken, PushProviderKind} from './push';

let registered: string | null = null;

/** Registers the token for the provider; false if there is none. */
export async function registerDevice(
  provider: PushProviderKind,
): Promise<boolean> {
  if (provider === 'disabled') return false;
  const token = await getPushToken(provider);
  if (!token) return false;
  const result = await fetchClient
    .POST('/v1/me/devices', {
      body: {token, platform: devicePlatform(), provider},
    })
    .catch(() => null);
  if (!result?.response.ok) return false;
  registered = token;
  return true;
}

/** Removes the registered token before signing out; errors are ignored. */
export async function unregisterDevice(): Promise<void> {
  const token = registered;
  if (!token) return;
  registered = null;
  await fetchClient
    .DELETE('/v1/me/devices/{token}', {params: {path: {token}}})
    .catch(() => null);
}
