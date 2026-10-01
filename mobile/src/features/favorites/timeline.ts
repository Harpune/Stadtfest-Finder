/**
 * Timeline "Deine Festsaison" (R06-US3): favorites grouped by month, split into past and
 * upcoming (running and future) relative to today (Europe/Berlin).
 */
import type {components} from '@/api/generated/schema';
import {formatMonthYear, IsoDate} from '@/features/events/dates';

export type FavoriteEntry = components['schemas']['FavoriteEntry'];

export interface MonthGroup {
  /** "September 2026" */
  title: string;
  entries: FavoriteEntry[];
}

export interface Timeline {
  /** Ended before today, oldest first. */
  past: MonthGroup[];
  /** Running and future, by start date. */
  upcoming: MonthGroup[];
  pastCount: number;
  upcomingCount: number;
}

function byStart(a: FavoriteEntry, b: FavoriteEntry): number {
  return (
    a.startDate.localeCompare(b.startDate) || a.name.localeCompare(b.name, 'de')
  );
}

function groupByMonth(entries: FavoriteEntry[]): MonthGroup[] {
  const groups: MonthGroup[] = [];
  for (const entry of entries) {
    const title = formatMonthYear(entry.startDate);
    const last = groups[groups.length - 1];
    if (last && last.title === title) last.entries.push(entry);
    else groups.push({title, entries: [entry]});
  }
  return groups;
}

/** Builds the timeline; an event ending today still counts as upcoming (running). */
export function buildTimeline(
  favorites: FavoriteEntry[],
  today: IsoDate,
): Timeline {
  const sorted = [...favorites].sort(byStart);
  const past = sorted.filter(entry => entry.endDate < today);
  const upcoming = sorted.filter(entry => entry.endDate >= today);
  return {
    past: groupByMonth(past),
    upcoming: groupByMonth(upcoming),
    pastCount: past.length,
    upcomingCount: upcoming.length,
  };
}
