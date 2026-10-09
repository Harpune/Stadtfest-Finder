/**
 * Friends (R12-US3, design gap: built like the other sub pages): list with avatars in the
 * friend palette, "+ Freund hinzufügen", swipe to remove with confirmation.
 */
import {router, useFocusEffect} from 'expo-router';
import React, {useCallback, useState} from 'react';
import {
  ActivityIndicator,
  Alert,
  FlatList,
  StyleSheet,
  View,
} from 'react-native';
import {useSafeAreaInsets} from 'react-native-safe-area-context';

import {
  Button,
  EmptyState,
  FriendRow,
  Icon,
  IconButton,
  SwipeToDelete,
  Text,
} from '@/components';
import {strings} from '@/strings/de';
import {useTheme} from '@/theme';

import {AddFriendSheet} from './AddFriendSheet';
import {
  displayName,
  friendColor,
  friendsSince,
  initialsOfName,
} from './friends';
import {Friend, useFriends, useRemoveFriend} from './useFriends';

const s = strings.friends;

export function FriendsScreen() {
  const theme = useTheme();
  const insets = useSafeAreaInsets();
  const friends = useFriends();
  const remove = useRemoveFriend();
  const [adding, setAdding] = useState(false);
  // The sheet lives above the navigation: close it when another screen opens on top.
  useFocusEffect(useCallback(() => () => setAdding(false), []));

  const confirmRemove = (friend: Friend) => {
    const name = displayName(friend.firstName, friend.lastName);
    Alert.alert(s.removeTitle, s.removeText(name), [
      {text: s.cancel, style: 'cancel'},
      {
        text: s.removeConfirm,
        style: 'destructive',
        onPress: () => void remove(friend),
      },
    ]);
  };

  let body: React.ReactNode = null;
  if (friends.isPending) {
    body = <ActivityIndicator testID="friends.loading" />;
  } else if (friends.isError) {
    body = (
      <View style={styles.gap}>
        <Text variant="body" tone="muted">
          {s.loadFailed}
        </Text>
        <Button
          label={s.retry}
          variant="secondary"
          onPress={() => void friends.refetch()}
          testID="friends.retry"
        />
      </View>
    );
  } else if (friends.data.items.length === 0) {
    body = (
      <EmptyState
        title={s.emptyTitle}
        text={s.emptyText}
        primary={{
          label: s.add,
          onPress: () => setAdding(true),
          testID: 'friends.empty.add',
        }}
        testID="friends.empty"
      />
    );
  }

  return (
    <View
      style={[styles.screen, {backgroundColor: theme.colors.background}]}
      testID="friends.screen"
    >
      <FlatList
        data={body ? [] : (friends.data?.items ?? [])}
        keyExtractor={item => item.id}
        contentContainerStyle={[
          styles.content,
          {paddingTop: insets.top + 8, paddingBottom: insets.bottom + 24},
        ]}
        ListHeaderComponent={
          <View style={styles.top}>
            <View style={styles.header}>
              <IconButton
                icon={<Icon name="chevronLeft" size={22} />}
                accessibilityLabel={strings.detail.back}
                onPress={() => router.back()}
                variant="surface"
                testID="friends.back"
              />
              <Text variant="displayM" style={styles.title}>
                {s.title}
              </Text>
            </View>
            {body ? null : (
              <Button
                label={s.add}
                variant="secondary"
                onPress={() => setAdding(true)}
                testID="friends.add"
              />
            )}
            {body}
          </View>
        }
        renderItem={({item}) => (
          <SwipeToDelete
            label={s.remove}
            onDelete={() => confirmRemove(item)}
            testID={`friends.swipe.${item.id}`}
          >
            <FriendRow
              name={displayName(item.firstName, item.lastName)}
              initials={initialsOfName(item.firstName, item.lastName)}
              color={friendColor(item.id, theme.colors)}
              meta={friendsSince(item.since)}
              testID={`friends.item.${item.id}`}
            />
          </SwipeToDelete>
        )}
        ItemSeparatorComponent={() => <View style={styles.separator} />}
      />
      <AddFriendSheet visible={adding} onClose={() => setAdding(false)} />
    </View>
  );
}

const styles = StyleSheet.create({
  screen: {flex: 1},
  content: {paddingHorizontal: 16},
  top: {gap: 16, marginBottom: 16},
  header: {flexDirection: 'row', alignItems: 'center', gap: 12},
  title: {flex: 1},
  gap: {gap: 12},
  separator: {height: 8},
});
