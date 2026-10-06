import {formatNotificationTime} from './time';

const NOW = new Date('2026-09-23T16:30:00Z'); // Wednesday 18:30 in Berlin

describe('formatNotificationTime', () => {
  it.each([
    ['2026-09-23T16:29:40Z', 'Gerade eben'],
    ['2026-09-23T16:18:00Z', 'vor 12 Min.'],
    ['2026-09-23T15:20:00Z', 'vor 1 Std.'],
    ['2026-09-23T07:00:00Z', 'Heute, 9:00'],
    ['2026-09-22T19:00:00Z', 'Gestern'],
    ['2026-09-21T08:00:00Z', 'Mo, 21.09.'],
  ])('%s -> %s', (createdAt, expected) => {
    expect(formatNotificationTime(createdAt, NOW)).toBe(expected);
  });
});
