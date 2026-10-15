/** "Neue Liste" (05-02): name and friends with checks; creates the list and opens it. */
import React, {useState} from 'react';
import {StyleSheet, View} from 'react-native';

import {
  Avatar,
  BottomSheet,
  Button,
  CheckRow,
  Text,
  TextField,
} from '@/components';
import {
  friendColor,
  initialsOfName,
  displayName,
} from '@/features/friends/friends';
import {useFriends} from '@/features/friends/useFriends';
import {navigate} from '@/features/navigation/navigate';
import {strings} from '@/strings/de';
import {useTheme} from '@/theme';

import {useCreateList} from './useLists';

const s = strings.lists;
const NAME_MAX = 60;

export function NewListSheet({
  visible,
  onClose,
}: {
  visible: boolean;
  onClose: () => void;
}) {
  const theme = useTheme();
  const friends = useFriends();
  const create = useCreateList();
  const [name, setName] = useState('');
  const [selected, setSelected] = useState<string[]>([]);
  const [busy, setBusy] = useState(false);

  const toggle = (id: string) =>
    setSelected(current =>
      current.includes(id) ? current.filter(x => x !== id) : [...current, id],
    );

  const submit = async () => {
    setBusy(true);
    const id = await create(name.trim(), selected);
    setBusy(false);
    if (!id) return;
    setName('');
    setSelected([]);
    onClose();
    navigate({pathname: '/listen/[id]', params: {id}});
  };

  const items = friends.data?.items ?? [];
  return (
    <BottomSheet
      visible={visible}
      onClose={onClose}
      title={s.newTitle}
      testID="lists.new.sheet"
      footer={
        <Button
          label={s.create}
          onPress={() => void submit()}
          disabled={name.trim().length === 0}
          loading={busy}
          testID="lists.new.create"
        />
      }
    >
      <TextField
        label={s.nameLabel}
        hideLabel
        placeholder={s.namePlaceholder}
        value={name}
        onChangeText={setName}
        maxLength={NAME_MAX}
        testID="lists.new.name"
      />
      <View>
        <Text variant="label">{s.addFriends}</Text>
        {items.length === 0 && friends.isSuccess ? (
          <Text variant="meta" tone="muted" style={styles.hint}>
            {s.noFriends}
          </Text>
        ) : null}
        {items.map(friend => (
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
            checked={selected.includes(friend.id)}
            onPress={() => toggle(friend.id)}
            testID={`lists.new.friend.${friend.id}`}
          />
        ))}
      </View>
    </BottomSheet>
  );
}

const styles = StyleSheet.create({hint: {marginTop: 8}});
