import {
  comingAlongText,
  eventMetaText,
  groupInvitees,
  invitationLinkUrl,
  inviteeMeta,
  whenText,
} from './format';
import type {Invitee} from './useInvitations';

const person = (firstName: string) => ({
  id: firstName,
  firstName,
  lastName: 'X',
});

describe('invitation format', () => {
  it('builds the link with the /e/ prefix', () => {
    expect(invitationLinkUrl('abc_DEF-123')).toBe(
      'https://stadtfest.herderstreet.de/e/abc_DEF-123',
    );
  });

  it('names up to two people, then counts', () => {
    expect(comingAlongText([person('Jonas')])).toBe('Jonas kommt mit');
    expect(comingAlongText([person('Jonas'), person('Tim')])).toBe(
      'Jonas und Tim kommen mit',
    );
    expect(
      comingAlongText([
        person('Jonas'),
        person('Tim'),
        person('Mia'),
        person('Can'),
      ]),
    ).toBe('Jonas, Tim und 2 weitere kommen mit');
  });

  it('describes when the event takes place', () => {
    const event = {startDate: '2026-10-17', endDate: '2026-10-18'};
    expect(whenText(event, '2026-10-09')).toBe('In 8 Tagen');
    expect(whenText(event, '2026-10-16')).toBe('Morgen');
    expect(whenText(event, '2026-10-17')).toBe('Heute');
    expect(whenText(event, '2026-10-18')).toBe('Läuft gerade');
    expect(whenText(event, '2026-10-19')).toBe('Vorbei');
    expect(eventMetaText({...event, city: 'Ulm'})).toBe('17.–18. Okt · Ulm');
  });

  it('groups invitees and explains their state', () => {
    const at = '2026-10-09T10:00:00Z';
    const invitees: Invitee[] = [
      {person: person('A'), status: 'open', invitedAt: at},
      {person: person('B'), status: 'accepted', invitedAt: at},
      {person: person('C'), status: 'declined', invitedAt: at},
    ];
    const groups = groupInvitees(invitees);
    expect(groups.accepted.map(i => i.person.id)).toEqual(['B']);
    expect(groups.open.map(i => i.person.id)).toEqual(['A']);
    expect(groups.declined.map(i => i.person.id)).toEqual(['C']);
    expect(inviteeMeta(invitees[1]!)).toBe('hat zugesagt');
    expect(inviteeMeta(invitees[0]!, new Date('2026-10-09T12:00:00Z'))).toBe(
      'Eingeladen vor 2 Std.',
    );
  });
});
