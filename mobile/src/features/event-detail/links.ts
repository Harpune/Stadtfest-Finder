/**
 * External links of the detail page: share link, maps route (R04-US3) and website URL
 * validation. Pure functions, covered by unit tests.
 */

/** Public host of shared event links and Android App Links (00-docs/40-operations/deep-links-domain.md). */
export const LINK_HOST = 'stadtfest.herderstreet.de';

/** Link to an event, e.g. for the share sheet (R06). */
export function eventShareUrl(eventId: string): string {
  return `https://${LINK_HOST}/f/${encodeURIComponent(eventId)}`;
}

export interface RouteTarget {
  lat: number;
  lon: number;
  name: string;
}

/**
 * URL that opens the default maps app with the destination: Apple Maps on iOS, a `geo:`
 * intent on Android (Google Maps or any other maps app registered for it).
 */
export function mapsRouteUrl(
  platform: 'ios' | 'android',
  target: RouteTarget,
): string {
  const coords = `${target.lat},${target.lon}`;
  const name = encodeURIComponent(target.name);
  if (platform === 'ios') {
    return `https://maps.apple.com/?daddr=${coords}&q=${name}`;
  }
  return `geo:${coords}?q=${coords}(${name})`;
}

/**
 * Returns the URL if it is a valid http(s) URL with a host, otherwise null. Other schemes
 * (javascript:, file:, intent:, custom app schemes) are never opened (R04-US3).
 */
export function safeWebUrl(value: string | null | undefined): string | null {
  if (!value) return null;
  const trimmed = value.trim();
  const match = /^https?:\/\/([^/?#\s:@]+)(:\d+)?([/?#][^\s]*)?$/i.exec(
    trimmed,
  );
  if (!match) return null;
  const host = match[1] ?? '';
  return host.includes('.') ? trimmed : null;
}

/** Short host for display: "https://www.oktoberfest.de/de" -> "oktoberfest.de". */
export function displayHost(url: string): string {
  const match = /^https?:\/\/([^/?#:]+)/i.exec(url);
  return (match?.[1] ?? url).replace(/^www\./i, '');
}
