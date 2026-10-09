/** Friend helpers (R12): link URL, avatar color and display texts. */
import {LINK_HOST} from '@/features/event-detail/links';
import {monthShort} from '@/features/events/dates';
import {strings} from '@/strings/de';
import type {ThemeColors} from '@/theme';

/** Public link for the QR code and the share sheet; the token carries no personal data. */
export function friendLinkUrl(token: string): string {
  return `https://${LINK_HOST}/freund/${encodeURIComponent(token)}`;
}

/** Same color for the same friend on every device (from the ID, not the name). */
export function friendColor(id: string, colors: ThemeColors): string {
  const palette = Object.values(colors.friend);
  let hash = 0;
  for (const char of id) hash = (hash * 31 + char.charCodeAt(0)) >>> 0;
  return palette[hash % palette.length] ?? palette[0] ?? colors.primary;
}

export function initialsOfName(firstName: string, lastName: string): string {
  return `${firstName.charAt(0)}${lastName.charAt(0)}`.toUpperCase();
}

export function displayName(firstName: string, lastName: string): string {
  return `${firstName} ${lastName}`.trim();
}

/** "Befreundet seit Okt 2026". */
export function friendsSince(since: string): string {
  const date = new Date(since);
  return strings.friends.since(
    `${monthShort(date.getMonth() + 1)} ${date.getFullYear()}`,
  );
}
