/** Invitation helpers (R14): link URL, people, texts. Pure functions with unit tests. */
import type {StackPerson} from '@/components';
import {LINK_HOST} from '@/features/event-detail/links';
import {daysBetween, formatDateRange} from '@/features/events/dates';
import {friendColor, initialsOfName} from '@/features/friends/friends';
import {formatNotificationTime} from '@/features/notifications/time';
import {strings} from '@/strings/de';
import type {ThemeColors} from '@/theme';

import type {InvitationPerson, Invitee} from './useInvitations';

const s = strings.invitations;

/** Public invitation link for the share sheet; the token carries no personal data. */
export function invitationLinkUrl(token: string): string {
  return `https://${LINK_HOST}/e/${encodeURIComponent(token)}`;
}

/** "19. Sep – 4. Okt · München". */
export function eventMetaText(event: {
  startDate: string;
  endDate: string;
  city: string;
}): string {
  return `${formatDateRange(event.startDate, event.endDate)} · ${event.city}`;
}

/** "In 8 Tagen", "Morgen", "Heute", "Läuft gerade", "Vorbei". */
export function whenText(
  event: {startDate: string; endDate: string},
  today: string,
): string {
  if (event.endDate < today) return s.ended;
  if (event.startDate < today) return s.running;
  return s.inDays(daysBetween(today, event.startDate));
}

export function fullName(person: InvitationPerson): string {
  return `${person.firstName} ${person.lastName}`.trim();
}

export function personAvatar(
  person: InvitationPerson,
  colors: ThemeColors,
): StackPerson {
  return {
    id: person.id,
    initials: initialsOfName(person.firstName, person.lastName),
    color: friendColor(person.id, colors),
  };
}

/** Second line of an invitee in the overview (06-01). */
export function inviteeMeta(invitee: Invitee, now?: Date): string {
  if (invitee.status === 'accepted') return s.hasAccepted;
  if (invitee.status === 'declined') return s.hasDeclined;
  const time = formatNotificationTime(invitee.invitedAt, now);
  // "vor 2 Std." stays, "Gestern" / "Heute, 9:00" become lower case after "Eingeladen".
  return s.invitedAgo(time.charAt(0).toLowerCase() + time.slice(1));
}

/** "Jonas kommt mit", "Jonas und Tim kommen mit", "Jonas, Tim und 2 weitere kommen mit". */
export function comingAlongText(people: InvitationPerson[]): string {
  const names = people.map(p => p.firstName || '?');
  if (names.length <= 2) return s.comingAlong(names, 0);
  return s.comingAlong(names.slice(0, 2), names.length - 2);
}

/** Invitees grouped as in the overview: accepted, open, declined. */
export function groupInvitees(invitees: Invitee[]) {
  return {
    accepted: invitees.filter(i => i.status === 'accepted'),
    open: invitees.filter(i => i.status === 'open'),
    declined: invitees.filter(i => i.status === 'declined'),
  };
}
