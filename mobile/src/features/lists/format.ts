/** Display texts for list events (R13). */
import {
  formatDateRange,
  monthShort,
  parseIsoDate,
} from '@/features/events/dates';

import type {ListEvent} from './useLists';

/** "🎄 Ulm · 23. Nov – 22. Dez". */
export function eventMeta(event: ListEvent): string {
  return `${event.emoji} ${event.city} · ${formatDateRange(event.startDate, event.endDate)}`;
}

/** "🎄 Ulmer Weihnachtsmarkt · 23. Nov – 22. Dez" for the overview card. */
export function nextEventText(event: ListEvent): string {
  return `${event.emoji} ${event.name} · ${formatDateRange(event.startDate, event.endDate)}`;
}

/** Date block: day and upper-case short month of the start date. */
export function dateBlock(event: ListEvent): {day: string; month: string} {
  const {day, month} = parseIsoDate(event.startDate);
  return {day: String(day), month: monthShort(month).toUpperCase()};
}
