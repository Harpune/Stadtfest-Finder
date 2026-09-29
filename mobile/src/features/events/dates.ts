/**
 * Calendar-day helpers. All "today" logic uses Europe/Berlin (same rule as the backend).
 * API dates are plain `YYYY-MM-DD` strings without time zone.
 */

export type IsoDate = string;

const MS_PER_DAY = 86_400_000;

/** Short German month names as used in the design ("19. Sep – 4. Okt"). */
export const MONTHS_SHORT = [
  'Jan',
  'Feb',
  'Mär',
  'Apr',
  'Mai',
  'Jun',
  'Jul',
  'Aug',
  'Sep',
  'Okt',
  'Nov',
  'Dez',
] as const;

const berlinDate = new Intl.DateTimeFormat('en-CA', {
  timeZone: 'Europe/Berlin',
  year: 'numeric',
  month: '2-digit',
  day: '2-digit',
});

/** Current day in Europe/Berlin as `YYYY-MM-DD`. */
export function todayInBerlin(now: Date = new Date()): IsoDate {
  return berlinDate.format(now);
}

interface Ymd {
  year: number;
  month: number; // 1-12
  day: number;
}

const ISO_DATE = /^(\d{4})-(\d{2})-(\d{2})$/;

/** Parses `YYYY-MM-DD`. Throws on malformed input (API dates are validated by the spec). */
export function parseIsoDate(value: IsoDate): Ymd {
  const match = ISO_DATE.exec(value);
  if (!match) throw new Error(`Invalid date: ${value}`);
  return {
    year: Number(match[1]),
    month: Number(match[2]),
    day: Number(match[3]),
  };
}

/** Short month name for 1-12. */
export function monthShort(month: number): string {
  return MONTHS_SHORT[(month - 1 + 12) % 12] ?? '';
}

function toEpochDay(value: IsoDate): number {
  const {year, month, day} = parseIsoDate(value);
  return Date.UTC(year, month - 1, day) / MS_PER_DAY;
}

/** Whole days from `from` to `to` (negative if `to` is earlier). */
export function daysBetween(from: IsoDate, to: IsoDate): number {
  return toEpochDay(to) - toEpochDay(from);
}

/** "19. Sep" */
export function formatDayMonth(value: IsoDate): string {
  const {month, day} = parseIsoDate(value);
  return `${day}. ${monthShort(month)}`;
}

/**
 * Date range as in the design: "27. Sep", "11.–13. Sep", "19. Sep – 4. Okt".
 * Different years are not shown (events never span more than a few weeks).
 */
export function formatDateRange(start: IsoDate, end: IsoDate): string {
  if (start === end) return formatDayMonth(start);
  const s = parseIsoDate(start);
  const e = parseIsoDate(end);
  if (s.year === e.year && s.month === e.month) {
    return `${s.day}.–${e.day}. ${monthShort(e.month)}`;
  }
  return `${formatDayMonth(start)} – ${formatDayMonth(end)}`;
}
