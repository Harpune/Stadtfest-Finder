/** "Gemeinsame Listen" overview (05-01, R13-US1). */
import {router} from 'expo-router';
import React, {useState} from 'react';
import {ActivityIndicator, FlatList, StyleSheet, View} from 'react-native';
import {useSafeAreaInsets} from 'react-native-safe-area-context';

import {
  Button,
  EmptyState,
  Icon,
  IconButton,
  SharedListCard,
  Text,
} from '@/components';
import {useAuth} from '@/features/auth/AuthProvider';
import {navigate} from '@/features/navigation/navigate';
import {strings} from '@/strings/de';
import {useTheme} from '@/theme';

import {nextEventText} from './format';
import {NewListSheet} from './NewListSheet';
import {meFirst, stackPerson} from './people';
import {useLists} from './useLists';

const s = strings.lists;

export function ListsScreen() {
  const theme = useTheme();
  const insets = useSafeAreaInsets();
  const {user} = useAuth();
  const lists = useLists();
  const [creating, setCreating] = useState(false);

  let body: React.ReactNode = null;
  if (lists.isPending) {
    body = <ActivityIndicator testID="lists.loading" />;
  } else if (lists.isError) {
    body = (
      <View style={styles.gap}>
        <Text variant="body" tone="muted">
          {s.loadFailed}
        </Text>
        <Button
          label={s.retry}
          variant="secondary"
          onPress={() => void lists.refetch()}
          testID="lists.retry"
        />
      </View>
    );
  } else if (lists.data.length === 0) {
    body = (
      <EmptyState
        title={s.emptyTitle}
        text={s.emptyText}
        primary={{
          label: s.newButton,
          onPress: () => setCreating(true),
          testID: 'lists.empty.new',
        }}
        testID="lists.empty"
      />
    );
  }

  return (
    <View
      style={[styles.screen, {backgroundColor: theme.colors.background}]}
      testID="lists.screen"
    >
      <FlatList
        data={body ? [] : (lists.data ?? [])}
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
                testID="lists.back"
              />
              <Text variant="displayL" style={styles.title}>
                {s.title}
              </Text>
              <Button
                label={s.newButton}
                size="medium"
                onPress={() => setCreating(true)}
                testID="lists.new"
              />
            </View>
            <Text variant="body" tone="muted">
              {s.intro}
            </Text>
            {body}
          </View>
        }
        renderItem={({item}) => (
          <SharedListCard
            name={item.name}
            eventCount={item.eventCount}
            people={meFirst(item.members, user?.id).map(m =>
              stackPerson(m, user?.id, theme.colors),
            )}
            next={item.nextEvent ? nextEventText(item.nextEvent) : undefined}
            onPress={() =>
              navigate({pathname: '/listen/[id]', params: {id: item.id}})
            }
            testID={`lists.card.${item.id}`}
          />
        )}
        ItemSeparatorComponent={() => <View style={styles.separator} />}
      />
      <NewListSheet visible={creating} onClose={() => setCreating(false)} />
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
  separator: {height: 14},
});
