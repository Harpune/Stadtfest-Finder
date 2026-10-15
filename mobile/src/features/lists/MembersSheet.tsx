/** Members of a list (R13-US4): own friends with checks; every tap takes effect at once. */
import React from 'react';

import {Avatar, BottomSheet, CheckRow, Text} from '@/components';
import {
  displayName,
  friendColor,
  initialsOfName,
} from '@/features/friends/friends';
import {useFriends} from '@/features/friends/useFriends';
import {strings} from '@/strings/de';
import {useTheme} from '@/theme';

import type {ListMember} from './useLists';

const s = strings.lists;

export function MembersSheet({
  visible,
  onClose,
  members,
  onAdd,
  onRemove,
}: {
  visible: boolean;
  onClose: () => void;
  members: ListMember[];
  onAdd: (member: ListMember) => void;
  onRemove: (userId: string) => void;
}) {
  const theme = useTheme();
  const friends = useFriends();
  const memberIds = new Set(members.map(m => m.id));
  const items = friends.data?.items ?? [];
  return (
    <BottomSheet
      visible={visible}
      onClose={onClose}
      title={s.membersTitle}
      testID="list.members.sheet"
    >
      {items.length === 0 && friends.isSuccess ? (
        <Text variant="meta" tone="muted">
          {s.noFriends}
        </Text>
      ) : null}
      {items.map(friend => {
        const checked = memberIds.has(friend.id);
        return (
          <CheckRow
            key={friend.id}
            label={displayName(friend.firstName, friend.lastName)}
            lead={
              <Avatar
                initials={initialsOfName(friend.firstName, friend.lastName)}
                color={friendColor(friend.id, theme.colors)}
                size={40}
              />
            }
            checked={checked}
            onPress={() =>
              checked
                ? onRemove(friend.id)
                : onAdd({
                    id: friend.id,
                    firstName: friend.firstName,
                    lastName: friend.lastName,
                  })
            }
            testID={`list.members.friend.${friend.id}`}
          />
        );
      })}
    </BottomSheet>
  );
}
