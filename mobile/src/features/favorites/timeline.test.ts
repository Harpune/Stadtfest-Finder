import {formatWeekdayDate} from '@/features/events/dates';

import {buildTimeline, FavoriteEntry} from './timeline';

function entry(
  name: string,
  startDate: string,
  endDate: string,
  status: FavoriteEntry['status'] = 'published',
): FavoriteEntry {
  return {
    id: name,
    name,
    shortName: name,
    status,
    startDate,
    endDate,
    place: 'Marktplatz',
    city: 'Aalen',
    lat: 48.8,
    lon: 10.1,
    categoryId: 'c1',
    categoryName: 'Stadtfest',
    emoji: '🎪',
    favoritedAt: '2026-09-01T10:00:00Z',
  };
}

const TODAY = '2026-09-25';

describe('buildTimeline', () => {
  it('splits past and upcoming and groups by month in start order', () => {
    const timeline = buildTimeline(
      [
        entry('Weihnachtsmarkt', '2026-11-26', '2026-12-23'),
        entry('Ipfmesse', '2026-07-01', '2026-07-05'),
        entry('Oktoberfest', '2026-09-19', '2026-10-04'),
        entry('Gmünd', '2026-10-03', '2026-10-04'),
        entry('Bergkirchweih', '2026-05-21', '2026-06-01'),
        entry('Christkindlesmarkt', '2026-11-27', '2026-12-24'),
      ],
      TODAY,
    );

    expect(timeline.pastCount).toBe(2);
    expect(timeline.upcomingCount).toBe(4);
    expect(timeline.past.map(g => g.title)).toEqual(['Mai 2026', 'Juli 2026']);
    expect(timeline.upcoming.map(g => g.title)).toEqual([
      'September 2026',
      'Oktober 2026',
      'November 2026',
    ]);
    expect(timeline.upcoming[2]?.entries.map(e => e.name)).toEqual([
      'Weihnachtsmarkt',
      'Christkindlesmarkt',
    ]);
  });

  it('keeps an event that ends today as upcoming', () => {
    const timeline = buildTimeline(
      [entry('Letzter Tag', '2026-09-20', TODAY)],
      TODAY,
    );
    expect(timeline.upcomingCount).toBe(1);
    expect(timeline.pastCount).toBe(0);
  });

  it('is empty without favorites', () => {
    expect(buildTimeline([], TODAY)).toEqual({
      past: [],
      upcoming: [],
      pastCount: 0,
      upcomingCount: 0,
    });
  });
});

describe('formatWeekdayDate', () => {
  it('formats the today marker', () => {
    expect(formatWeekdayDate('2026-09-25')).toBe('FR 25.09.');
  });
});
