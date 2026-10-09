/**
 * Notification list (07-01, R11-US1): groups "Neu" and "Früher", "Alle als gelesen
 * markieren", a tap marks the entry read and opens the event.
 */
import {router} from 'expo-router';
import React, {useMemo} from 'react';
import {
  ActivityIndicator,
  Pressable,
  RefreshControl,
  SectionList,
  StyleSheet,
  View,
} from 'react-native';
import {useSafeAreaInsets} from 'react-native-safe-area-context';

import {
  Button,
  EmptyState,
  Icon,
  IconButton,
  NotificationRow,
  SwipeToDelete,
  SectionHeader,
  Text,
} from '@/components';
import {navigate} from '@/features/navigation/navigate';
import {strings} from '@/strings/de';
import {useTheme} from '@/theme';

import {formatNotificationTime} from './time';
import {
  AppNotification,
  useDeleteNotification,
  useMarkRead,
  useNotificationList,
  useUnreadCount,
} from './useNotifications';

export interface NotificationsScreenProps {
  /** Injectable "now" for tests. */
  now?: Date;
}

// Notification types are extensible (ADR 0017): unknown ones get a neutral look.
const ICONS: Record<string, string | undefined> = strings.notifications.icons;
const KINDS: Record<string, string | undefined> = strings.notifications.kinds;
const iconOf = (type: string) =>
  ICONS[type] ?? strings.notifications.unknownIcon;
const kindOf = (type: string) =>
  KINDS[type] ?? strings.notifications.unknownKind;

export function NotificationsScreen({now}: NotificationsScreenProps) {
  const theme = useTheme();
  const insets = useSafeAreaInsets();
  const list = useNotificationList();
  const unread = useUnreadCount();
  const markRead = useMarkRead();
  const deleteNotification = useDeleteNotification();
  const s = strings.notifications;

  const sections = useMemo(() => {
    const items = list.data?.pages.flatMap(page => page.items) ?? [];
    return [
      {key: 'new', title: s.groupNew, data: items.filter(i => !i.read)},
      {key: 'earlier', title: s.groupEarlier, data: items.filter(i => i.read)},
    ].filter(section => section.data.length > 0);
  }, [list.data, s.groupNew, s.groupEarlier]);

  const open = (item: AppNotification) => {
    if (!item.read) void markRead(item.id);
    // Unknown target types (ADR 0017) only mark the entry read.
    const target: string = item.target.type;
    if (target === 'friend') navigate('/freunde');
    if (target === 'list') {
      navigate({pathname: '/listen/[id]', params: {id: item.target.id}});
    }
    if (target === 'invitation') {
      navigate({pathname: '/einladung/[id]', params: {id: item.target.id}});
    }
    if (target === 'invitationOverview') {
      navigate({
        pathname: '/einladen/[eventId]',
        params: {eventId: item.target.id},
      });
    }
    if (target === 'event') {
      navigate({pathname: '/f/[id]', params: {id: item.target.id}});
    }
  };

  const header = (
    <View style={styles.header}>
      <IconButton
        icon={<Icon name="chevronLeft" size={22} />}
        accessibilityLabel={strings.detail.back}
        onPress={() => router.back()}
        variant="surface"
        testID="notifications.back"
      />
      <Text variant="displayM" style={styles.title}>
        {s.title}
      </Text>
      <IconButton
        icon={<Icon name="settings" size={22} />}
        accessibilityLabel={s.settings}
        onPress={() => navigate('/benachrichtigungen/einstellungen')}
        variant="surface"
        testID="notifications.settings"
      />
    </View>
  );

  let body: React.ReactNode = null;
  if (list.isPending) {
    body = <ActivityIndicator testID="notifications.loading" />;
  } else if (list.isError) {
    body = (
      <View style={styles.message}>
        <Text variant="body" tone="muted">
          {s.loadFailed}
        </Text>
        <Button
          label={s.retry}
          variant="secondary"
          onPress={() => void list.refetch()}
          testID="notifications.retry"
        />
      </View>
    );
  } else if (sections.length === 0) {
    body = (
      <EmptyState
        title={s.emptyTitle}
        text={s.emptyText}
        testID="notifications.empty"
      />
    );
  }

  return (
    <View
      style={[styles.screen, {backgroundColor: theme.colors.background}]}
      testID="notifications.screen"
    >
      <SectionList
        sections={body ? [] : sections}
        keyExtractor={item => item.id}
        contentContainerStyle={[
          styles.content,
          {paddingTop: insets.top + 8, paddingBottom: insets.bottom + 24},
        ]}
        ListHeaderComponent={
          <View style={styles.top}>
            {header}
            {unread > 0 ? (
              <Pressable
                accessibilityRole="button"
                onPress={() => void markRead(null)}
                testID="notifications.readAll"
                style={styles.readAll}
              >
                <Text variant="bodyStrong" tone="primary">
                  {s.markAllRead}
                </Text>
              </Pressable>
            ) : null}
            {body}
          </View>
        }
        renderSectionHeader={({section}) => (
          <SectionHeader
            title={section.title}
            testID={`notifications.group.${section.key}`}
          />
        )}
        renderItem={({item}) => (
          <SwipeToDelete
            label={s.delete}
            onDelete={() => void deleteNotification(item)}
            testID={`notifications.swipe.${item.id}`}
          >
            <NotificationRow
              icon={iconOf(item.type)}
              kind={kindOf(item.type)}
              text={item.text}
              time={formatNotificationTime(item.createdAt, now)}
              unread={!item.read}
              tone={item.type === 'cancel' ? 'alert' : 'default'}
              onPress={() => open(item)}
              testID={`notifications.item.${item.id}`}
            />
          </SwipeToDelete>
        )}
        onEndReached={() => {
          if (list.hasNextPage && !list.isFetchingNextPage) {
            void list.fetchNextPage();
          }
        }}
        stickySectionHeadersEnabled={false}
        refreshControl={
          <RefreshControl
            refreshing={list.isRefetching && !list.isFetchingNextPage}
            onRefresh={() => void list.refetch()}
            tintColor={theme.colors.primary}
          />
        }
      />
    </View>
  );
}

const styles = StyleSheet.create({
  screen: {flex: 1},
  content: {paddingHorizontal: 16, gap: 4},
  top: {gap: 12, marginBottom: 4},
  header: {flexDirection: 'row', alignItems: 'center', gap: 12},
  title: {flex: 1},
  readAll: {alignSelf: 'flex-end', minHeight: 44, justifyContent: 'center'},
  message: {gap: 12, alignItems: 'flex-start'},
});
