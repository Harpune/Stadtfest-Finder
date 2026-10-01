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

/** Full German month names ("19. September – 4. Oktober 2026"). */
const MONTHS_LONG = [
  'Januar',
  'Februar',
  'März',
  'April',
  'Mai',
  'Juni',
  'Juli',
  'August',
  'September',
  'Oktober',
  'November',
  'Dezember',
] as const;

const WEEKDAYS_SHORT = ['SO', 'MO', 'DI', 'MI', 'DO', 'FR', 'SA'] as const;

function monthLong(month: number): string {
  return MONTHS_LONG[(month - 1 + 12) % 12] ?? '';
}

/**
 * Long date range for the detail page: "27. September 2026", "11.–13. September 2026",
 * "19. September – 4. Oktober 2026", "28. Dezember 2026 – 2. Januar 2027".
 */
export function formatDateRangeLong(start: IsoDate, end: IsoDate): string {
  const s = parseIsoDate(start);
  const e = parseIsoDate(end);
  if (start === end) return `${s.day}. ${monthLong(s.month)} ${s.year}`;
  if (s.year !== e.year) {
    return `${s.day}. ${monthLong(s.month)} ${s.year} – ${e.day}. ${monthLong(e.month)} ${e.year}`;
  }
  if (s.month === e.month) {
    return `${s.day}.–${e.day}. ${monthLong(e.month)} ${e.year}`;
  }
  return `${s.day}. ${monthLong(s.month)} – ${e.day}. ${monthLong(e.month)} ${e.year}`;
}

/** Program date block: weekday "SA" and day "19.9.". */
export function formatProgramDate(value: IsoDate): {
  weekday: string;
  day: string;
} {
  const {year, month, day} = parseIsoDate(value);
  const weekday = new Date(Date.UTC(year, month - 1, day)).getUTCDay();
  return {weekday: WEEKDAYS_SHORT[weekday] ?? '', day: `${day}.${month}.`};
}

/** Month heading of the timeline: "September 2026". */
export function formatMonthYear(value: IsoDate): string {
  const {year, month} = parseIsoDate(value);
  return `${monthLong(month)} ${year}`;
}

/** Day marker of the timeline: "FR 25.09.". */
export function formatWeekdayDate(value: IsoDate): string {
  const {weekday} = formatProgramDate(value);
  const {month, day} = parseIsoDate(value);
  const pad = (n: number) => String(n).padStart(2, '0');
  return `${weekday} ${pad(day)}.${pad(month)}.`;
}
