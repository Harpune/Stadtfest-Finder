/** People of shared lists: avatars and labels (R13). */
import type {StackPerson} from '@/components';
import {friendColor, initialsOfName} from '@/features/friends/friends';
import {strings} from '@/strings/de';
import type {ThemeColors} from '@/theme';

import type {ListMember} from './useLists';

/** The own account keeps the neutral user color, others get their friend color. */
export function stackPerson(
  member: ListMember,
  meId: string | undefined,
  colors: ThemeColors,
): StackPerson {
  return {
    id: member.id,
    initials: initialsOfName(member.firstName, member.lastName),
    color: member.id === meId ? undefined : friendColor(member.id, colors),
  };
}

/** Own account first, as in the design ("Du", then the others). */
export function meFirst(members: ListMember[], meId: string | undefined) {
  return [...members].sort(
    (a, b) => Number(b.id === meId) - Number(a.id === meId),
  );
}

export function memberLabel(member: ListMember, meId: string | undefined) {
  return member.id === meId ? strings.lists.you : member.firstName || '?';
}
