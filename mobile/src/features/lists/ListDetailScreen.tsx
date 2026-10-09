/**
 * A shared list (05-03) with its edit mode (05-04): members, events chronologically,
 * "Bearbeiten" turns the name into a field and shows ✕ at members and events, "Liste
 * löschen" and "Liste verlassen" (assumption, not designed).
 */
import {router} from 'expo-router';
import React, {useState} from 'react';
import {
  ActivityIndicator,
  Alert,
  Pressable,
  ScrollView,
  StyleSheet,
  View,
} from 'react-native';
import {useSafeAreaInsets} from 'react-native-safe-area-context';

import {
  Button,
  Icon,
  IconButton,
  ListEventRow,
  MemberAvatar,
  Text,
  TextField,
  useToast,
} from '@/components';
import {useAuth} from '@/features/auth/AuthProvider';
import {todayInBerlin} from '@/features/events/dates';
import {navigate} from '@/features/navigation/navigate';
import {strings} from '@/strings/de';
import {useTheme} from '@/theme';

import {EventsSheet} from './EventsSheet';
import {dateBlock, eventMeta} from './format';
import {MembersSheet} from './MembersSheet';
import {meFirst, memberLabel, stackPerson} from './people';
import {SharedList, useList, useListActions} from './useLists';

const s = strings.lists;
const NAME_MAX = 60;

export function ListDetailScreen({listId}: {listId: string}) {
  const theme = useTheme();
  const insets = useSafeAreaInsets();
  const list = useList(listId);

  const back = () => (router.canGoBack() ? router.back() : router.replace('/'));

  let content: React.ReactNode;
  if (list.isPending) {
    content = <ActivityIndicator style={styles.padded} testID="list.loading" />;
  } else if (list.isError || !list.data) {
    content = (
      <View style={[styles.gap, styles.padded]} testID="list.notFound">
        <Text variant="displayM">{s.notFound}</Text>
        <Button
          label={strings.common.close}
          variant="secondary"
          onPress={back}
          testID="list.notFound.close"
        />
      </View>
    );
  } else {
    content = <ListContent list={list.data} onBack={back} />;
  }

  return (
    <View
      style={[
        styles.screen,
        {
          backgroundColor: theme.colors.background,
          paddingTop: insets.top + 8,
        },
      ]}
      testID="list.screen"
    >
      {list.data ? null : (
        <View style={[styles.header, styles.padded]}>
          <IconButton
            icon={<Icon name="chevronLeft" size={22} />}
            accessibilityLabel={strings.detail.back}
            onPress={back}
            variant="surface"
            testID="list.back"
          />
        </View>
      )}
      {content}
    </View>
  );
}

function ListContent({list, onBack}: {list: SharedList; onBack: () => void}) {
  const theme = useTheme();
  const c = theme.colors;
  const insets = useSafeAreaInsets();
  const toast = useToast();
  const {user} = useAuth();
  const actions = useListActions(list.id);
  const [editing, setEditing] = useState(false);
  const [name, setName] = useState(list.name);
  const [sheet, setSheet] = useState<'members' | 'events' | null>(null);
  const today = todayInBerlin();
  const meId = user?.id;
  const members = meFirst(list.members, meId);

  const saveName = () => {
    const cleaned = name.trim();
    if (!cleaned || cleaned === list.name) {
      setName(list.name);
      return;
    }
    void actions.rename(cleaned);
  };

  const finish = () => {
    saveName();
    setEditing(false);
  };

  const confirmDelete = () =>
    Alert.alert(s.deleteTitle, s.deleteText(list.name), [
      {text: s.cancel, style: 'cancel'},
      {
        text: s.deleteConfirm,
        style: 'destructive',
        onPress: async () => {
          if (await actions.remove()) {
            toast(s.deleted);
            onBack();
          }
        },
      },
    ]);

  const confirmLeave = () =>
    Alert.alert(s.leaveTitle, s.leaveText, [
      {text: s.cancel, style: 'cancel'},
      {
        text: s.leaveConfirm,
        style: 'destructive',
        onPress: async () => {
          if (meId && (await actions.removeMember(meId))) {
            toast(s.left);
            onBack();
          }
        },
      },
    ]);

  return (
    <>
      <ScrollView
        keyboardShouldPersistTaps="handled"
        contentContainerStyle={[
          styles.content,
          {paddingBottom: insets.bottom + 24},
        ]}
      >
        <View style={styles.header}>
          <IconButton
            icon={<Icon name="chevronLeft" size={22} />}
            accessibilityLabel={strings.detail.back}
            onPress={onBack}
            variant="surface"
            testID="list.back"
          />
          <View style={styles.spacer} />
          <Button
            label={editing ? s.done : s.edit}
            variant={editing ? 'primary' : 'secondary'}
            size="medium"
            onPress={editing ? finish : () => setEditing(true)}
            testID={editing ? 'list.done' : 'list.edit'}
          />
        </View>

        {editing ? (
          <TextField
            label={s.nameLabel}
            hideLabel
            value={name}
            onChangeText={setName}
            onSubmitEditing={saveName}
            maxLength={NAME_MAX}
            testID="list.name.input"
          />
        ) : (
          <Text variant="displayXL" testID="list.name">
            {list.name}
          </Text>
        )}

        <View style={styles.sectionHeader}>
          <Text variant="label">{s.members(list.members.length)}</Text>
          <Link
            label={s.addMember}
            onPress={() => setSheet('members')}
            testID="list.members.add"
          />
        </View>
        <ScrollView horizontal showsHorizontalScrollIndicator={false}>
          <View style={styles.members}>
            {members.map(member => {
              const person = stackPerson(member, meId, c);
              return (
                <MemberAvatar
                  key={member.id}
                  initials={person.initials}
                  color={person.color}
                  label={memberLabel(member, meId)}
                  onRemove={
                    editing && member.id !== meId
                      ? () => void actions.removeMember(member.id)
                      : undefined
                  }
                  testID={`list.member.${member.id}`}
                />
              );
            })}
          </View>
        </ScrollView>

        <View style={styles.sectionHeader}>
          <Text variant="label">{s.eventsHeader}</Text>
          <Link
            label={s.addEvent}
            onPress={() => setSheet('events')}
            testID="list.events.add"
          />
        </View>
        {list.events.length === 0 ? (
          <Text variant="body" tone="muted">
            {s.noEvents}
          </Text>
        ) : null}
        <View style={styles.events}>
          {list.events.map(event => (
            <ListEventRow
              key={event.id}
              {...dateBlock(event)}
              name={event.name}
              meta={eventMeta(event)}
              past={event.endDate < today}
              cancelled={event.status === 'cancelled'}
              onPress={() =>
                navigate({pathname: '/f/[id]', params: {id: event.id}})
              }
              onRemove={
                editing ? () => void actions.removeEvent(event.id) : undefined
              }
              testID={`list.event.${event.id}`}
            />
          ))}
        </View>

        {editing ? (
          <View style={styles.gap}>
            <Button
              label={s.delete}
              variant="danger"
              onPress={confirmDelete}
              testID="list.delete"
            />
            <Button
              label={s.leave}
              variant="ghost"
              onPress={confirmLeave}
              testID="list.leave"
            />
          </View>
        ) : null}
        <Text variant="meta" tone="muted" style={styles.footer}>
          {s.footer}
        </Text>
      </ScrollView>

      <MembersSheet
        visible={sheet === 'members'}
        onClose={() => setSheet(null)}
        members={list.members}
        onAdd={member => void actions.addMember(member)}
        onRemove={userId => void actions.removeMember(userId)}
      />
      <EventsSheet
        visible={sheet === 'events'}
        onClose={() => setSheet(null)}
        selected={new Set(list.events.map(e => e.id))}
        onAdd={event => void actions.addEvent(event)}
        onRemove={eventId => void actions.removeEvent(eventId)}
      />
    </>
  );
}

function Link({
  label,
  onPress,
  testID,
}: {
  label: string;
  onPress: () => void;
  testID: string;
}) {
  return (
    <Pressable
      accessibilityRole="button"
      onPress={onPress}
      hitSlop={10}
      testID={testID}
    >
      <Text variant="bodyStrong" tone="primary">
        {label}
      </Text>
    </Pressable>
  );
}

const styles = StyleSheet.create({
  screen: {flex: 1},
  padded: {paddingHorizontal: 16, marginBottom: 16},
  content: {paddingHorizontal: 16, gap: 18},
  header: {flexDirection: 'row', alignItems: 'center', gap: 12},
  spacer: {flex: 1},
  sectionHeader: {
    flexDirection: 'row',
    alignItems: 'center',
    justifyContent: 'space-between',
    marginTop: 6,
  },
  members: {flexDirection: 'row', gap: 12},
  events: {gap: 10},
  gap: {gap: 12},
  footer: {textAlign: 'center', marginTop: 8},
});
