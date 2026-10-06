/**
 * Relative time of a notification as in the design (07-01): "vor 12 Min.", "vor 1 Std.",
 * "Heute, 9:00", "Gestern", "Mo, 21.09.". Days follow Europe/Berlin.
 */
import {daysBetween, todayInBerlin} from '@/features/events/dates';
import {strings} from '@/strings/de';

const WEEKDAYS = ['So', 'Mo', 'Di', 'Mi', 'Do', 'Fr', 'Sa'] as const;

const berlinParts = new Intl.DateTimeFormat('en-GB', {
  timeZone: 'Europe/Berlin',
  weekday: 'short',
  day: '2-digit',
  month: '2-digit',
  hour: 'numeric',
  minute: '2-digit',
  hour12: false,
});

const EN_WEEKDAYS = ['Sun', 'Mon', 'Tue', 'Wed', 'Thu', 'Fri', 'Sat'];

function parts(date: Date) {
  const values: Record<string, string> = {};
  for (const part of berlinParts.formatToParts(date)) {
    values[part.type] = part.value;
  }
  return {
    weekday: WEEKDAYS[EN_WEEKDAYS.indexOf(values.weekday ?? '')] ?? '',
    day: values.day ?? '',
    month: values.month ?? '',
    // "24" at midnight in some engines.
    time: `${Number(values.hour ?? 0) % 24}:${values.minute ?? '00'}`,
  };
}

export function formatNotificationTime(
  createdAt: string,
  now: Date = new Date(),
): string {
  const created = new Date(createdAt);
  const minutes = Math.floor((now.getTime() - created.getTime()) / 60_000);
  const t = strings.notifications.time;
  if (minutes < 1) return t.justNow;
  if (minutes < 60) return t.minutes(minutes);
  if (minutes < 180) return t.hours(Math.floor(minutes / 60));
  const days = daysBetween(todayInBerlin(created), todayInBerlin(now));
  const p = parts(created);
  if (days === 0) return t.today(p.time);
  if (days === 1) return t.yesterday;
  return `${p.weekday}, ${p.day}.${p.month}.`;
}
