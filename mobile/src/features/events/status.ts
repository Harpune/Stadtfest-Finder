/**
 * Status line of an event ("● Läuft · noch 9 Tage", "In 8 Tagen", "Ab 12. Okt", "Abgesagt").
 * Single source for carousel, list, detail and timeline (R03-US3).
 */
import {daysBetween, formatDayMonth, IsoDate} from './dates';

export type EventStatusTone =
  'running' | 'soon' | 'later' | 'cancelled' | 'past';

export interface EventStatusInfo {
  tone: EventStatusTone;
  /** Text without the leading dot; the UI adds "● " for `running`. */
  label: string;
}

export interface StatusInput {
  status: 'published' | 'cancelled';
  startDate: IsoDate;
  endDate: IsoDate;
}

/** Events starting within this many days show "In X Tagen". */
export const SOON_DAYS = 14;

/**
 * Computes the status line for `today` (Europe/Berlin).
 *
 * - cancelled: "Abgesagt"
 * - running (start <= today <= end): "Läuft · noch X Tage"; on the last day "Läuft · letzter Tag"
 * - starts in 1 day: "Morgen"; in 2-14 days: "In X Tagen"
 * - later: "Ab {Tag}. {Monat}"
 * - ended: "Vorbei" (past events appear only in timelines)
 */
export function eventStatus(
  event: StatusInput,
  today: IsoDate,
): EventStatusInfo {
  if (event.status === 'cancelled') {
    return {tone: 'cancelled', label: 'Abgesagt'};
  }
  const untilStart = daysBetween(today, event.startDate);
  const untilEnd = daysBetween(today, event.endDate);
  if (untilEnd < 0) {
    return {tone: 'past', label: 'Vorbei'};
  }
  if (untilStart <= 0) {
    if (untilEnd === 0) return {tone: 'running', label: 'Läuft · letzter Tag'};
    const unit = untilEnd === 1 ? 'Tag' : 'Tage';
    return {tone: 'running', label: `Läuft · noch ${untilEnd} ${unit}`};
  }
  if (untilStart === 1) return {tone: 'soon', label: 'Morgen'};
  if (untilStart <= SOON_DAYS) {
    return {tone: 'soon', label: `In ${untilStart} Tagen`};
  }
  return {tone: 'later', label: `Ab ${formatDayMonth(event.startDate)}`};
}

/** Whether the event takes place today (badge "● Läuft gerade"). */
export function isRunning(event: StatusInput, today: IsoDate): boolean {
  return eventStatus(event, today).tone === 'running';
}
