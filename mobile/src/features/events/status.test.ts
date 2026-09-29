import {daysBetween, formatDateRange, todayInBerlin} from './dates';
import {eventStatus} from './status';

const TODAY = '2026-09-25';

function status(start: string, end: string, cancelled = false) {
  return eventStatus(
    {
      status: cancelled ? 'cancelled' : 'published',
      startDate: start,
      endDate: end,
    },
    TODAY,
  );
}

describe('eventStatus', () => {
  it('shows remaining days for running events', () => {
    expect(status('2026-09-19', '2026-10-04')).toEqual({
      tone: 'running',
      label: 'Läuft · noch 9 Tage',
    });
  });

  it('handles the last two days of a running event', () => {
    expect(status('2026-09-20', '2026-09-26').label).toBe('Läuft · noch 1 Tag');
    expect(status('2026-09-20', TODAY).label).toBe('Läuft · letzter Tag');
  });

  it('treats an event starting today as running', () => {
    expect(status(TODAY, '2026-09-27').tone).toBe('running');
  });

  it('shows "Morgen" and "In X Tagen" up to 14 days', () => {
    expect(status('2026-09-26', '2026-09-27')).toEqual({
      tone: 'soon',
      label: 'Morgen',
    });
    expect(status('2026-10-03', '2026-10-04').label).toBe('In 8 Tagen');
    expect(status('2026-10-09', '2026-10-10').label).toBe('In 14 Tagen');
  });

  it('shows the start date from day 15 on', () => {
    expect(status('2026-10-10', '2026-10-12')).toEqual({
      tone: 'later',
      label: 'Ab 10. Okt',
    });
  });

  it('prefers "Abgesagt" over any other status', () => {
    expect(status('2026-09-19', '2026-10-04', true)).toEqual({
      tone: 'cancelled',
      label: 'Abgesagt',
    });
  });

  it('marks ended events as past', () => {
    expect(status('2026-09-20', '2026-09-24').tone).toBe('past');
  });

  it('counts calendar days across month and year ends', () => {
    expect(daysBetween('2026-12-31', '2027-01-01')).toBe(1);
    expect(status('2026-09-24', '2026-10-01').label).toBe(
      'Läuft · noch 6 Tage',
    );
  });
});

describe('formatDateRange', () => {
  it('formats single days, same-month and cross-month ranges', () => {
    expect(formatDateRange('2026-09-27', '2026-09-27')).toBe('27. Sep');
    expect(formatDateRange('2026-10-03', '2026-10-04')).toBe('3.–4. Okt');
    expect(formatDateRange('2026-09-19', '2026-10-04')).toBe(
      '19. Sep – 4. Okt',
    );
    expect(formatDateRange('2026-03-01', '2026-03-02')).toBe('1.–2. Mär');
  });
});

describe('todayInBerlin', () => {
  it('uses the Berlin calendar day, not UTC', () => {
    // 23:30 UTC on 25 Sep is already 26 Sep in Berlin (CEST, UTC+2).
    expect(todayInBerlin(new Date('2026-09-25T23:30:00Z'))).toBe('2026-09-26');
    expect(todayInBerlin(new Date('2026-12-31T22:59:00Z'))).toBe('2026-12-31');
  });
});
