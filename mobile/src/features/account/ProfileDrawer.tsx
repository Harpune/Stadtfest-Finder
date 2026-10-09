/**
 * Profile drawer: guest variant (03-07) with login; signed in (R06) with user row, the
 * bell with the unread counter next to the user (R11), the timeline "Deine Festsaison" and the
 * footer (dark mode, moderator view, logout). "Gemeinsame Listen" (R13) is not shown yet.
 * Deviation from the design: the notifications sit with the user, not in the footer.
 */
import React, {useCallback, useEffect, useState} from 'react';
import {Pressable, StyleSheet, View} from 'react-native';

import {
  Avatar,
  Button,
  Icon,
  IconButton,
  MenuRow,
  NotificationBell,
  SideDrawer,
  Skeleton,
  Text,
  useToast,
} from '@/components';
import {navigate} from '@/features/navigation/navigate';
import {initialsOf, useAuth} from '@/features/auth/AuthProvider';
import {todayInBerlin} from '@/features/events/dates';
import {FestSaison} from '@/features/favorites/FestSaison';
import {useFavorites} from '@/features/favorites/useFavorites';
import {useUnreadCount} from '@/features/notifications/useNotifications';
import {strings} from '@/strings/de';
import {useTheme, useThemePreference} from '@/theme';

import {NameSheet} from './NameSheet';

export interface ProfileDrawerProps {
  visible: boolean;
  /** `animated: false` when an entry opens another screen (that screen slides in alone). */
  onClose: (options?: {animated: boolean}) => void;
}

type Close = (options?: {animated: boolean}) => void;

export function ProfileDrawer({
  visible,
  onClose: closeDrawer,
}: ProfileDrawerProps) {
  const [animateClose, setAnimateClose] = useState(true);
  useEffect(() => {
    if (visible) setAnimateClose(true);
  }, [visible]);
  const onClose: Close = useCallback(
    options => {
      setAnimateClose(options?.animated ?? true);
      closeDrawer(options);
    },
    [closeDrawer],
  );
  const {status, user, logout, isModerator} = useAuth();
  const signedIn = status === 'signedIn';
  const theme = useTheme();
  const toast = useToast();
  const {setPreference} = useThemePreference();
  const [askName, setAskName] = useState(false);

  // First opening without a name (Apple without name sharing): ask for it once.
  const needsName = signedIn && user !== null && user.firstName === '';
  useEffect(() => {
    if (visible && needsName) setAskName(true);
  }, [visible, needsName]);

  const footer = signedIn ? (
    <View style={styles.footer}>
      <MenuRow
        label={strings.drawer.darkMode}
        switchValue={theme.scheme === 'dark'}
        onSwitchChange={dark => setPreference(dark ? 'dark' : 'light')}
        onLongPress={() => {
          setPreference('system');
          toast(strings.drawer.darkModeSystem);
        }}
        accessibilityHint={strings.drawer.darkModeHint}
        testID="drawer.darkMode"
      />
      {isModerator ? (
        <MenuRow
          label={strings.drawer.moderator}
          tone="primary"
          chevron
          onPress={() => {
            onClose({animated: false});
            navigate('/mod');
          }}
          testID="drawer.moderator"
        />
      ) : null}
      <MenuRow
        label={strings.drawer.logout}
        tone="secondary"
        onPress={async () => {
          onClose();
          await logout();
        }}
        testID="drawer.logout"
      />
    </View>
  ) : undefined;

  return (
    <>
      <SideDrawer
        visible={visible}
        onClose={() => onClose()}
        animateClose={animateClose}
        footer={footer}
        testID="drawer"
      >
        {signedIn ? (
          <SignedInContent onClose={onClose} />
        ) : (
          <GuestContent onClose={onClose} />
        )}
      </SideDrawer>
      <NameSheet visible={askName} onClose={() => setAskName(false)} />
    </>
  );
}

function CloseButton({onClose}: {onClose: Close}) {
  return (
    <IconButton
      icon={<Icon name="close" size={22} />}
      accessibilityLabel={strings.common.close}
      onPress={() => onClose()}
      variant="surface"
      testID="drawer.close"
    />
  );
}

function GuestContent({onClose}: {onClose: Close}) {
  const {openLogin} = useAuth();
  const theme = useTheme();
  return (
    <>
      <View style={styles.closeRow}>
        <CloseButton onClose={onClose} />
      </View>
      <Text variant="displayXL" testID="drawer.guest.title">
        {strings.drawer.guestTitle}
      </Text>
      <Text variant="body" tone="muted">
        {strings.drawer.guestText}
      </Text>
      {/* Hinted timeline (skeleton, opacity .5); the real timeline follows in R06. */}
      <View style={styles.timeline} accessibilityElementsHidden>
        {[theme.colors.primary, theme.colors.secondary].map(color => (
          <View key={color} style={styles.timelineItem}>
            <View style={[styles.dot, {borderColor: color}]} />
            <View style={styles.timelineText}>
              <Skeleton width="60%" height={14} />
              <Skeleton width="90%" height={18} />
            </View>
          </View>
        ))}
      </View>
      <Button
        label={strings.drawer.guestLogin}
        onPress={() => {
          onClose({animated: false});
          openLogin();
        }}
        testID="drawer.login"
      />
      <Text variant="meta" tone="muted" style={styles.center}>
        {strings.drawer.guestHint}
      </Text>
    </>
  );
}

function SignedInContent({onClose}: {onClose: Close}) {
  const {user, email} = useAuth();
  const unread = useUnreadCount();
  const favorites = useFavorites();
  const name = user ? `${user.firstName} ${user.lastName}`.trim() : '';
  return (
    <>
      <View style={styles.userRow}>
        <Pressable
          testID="drawer.user"
          accessibilityRole="button"
          accessibilityLabel={strings.drawer.openAccount}
          onPress={() => {
            onClose({animated: false});
            navigate('/konto');
          }}
          style={styles.user}
        >
          <Avatar initials={initialsOf(user)} size={32} />
          <View style={styles.userText}>
            <Text variant="bodyStrong" numberOfLines={1} testID="drawer.name">
              {name}
            </Text>
            {email ? (
              <Text variant="meta" tone="muted" numberOfLines={1}>
                {email}
              </Text>
            ) : null}
          </View>
        </Pressable>
        <IconButton
          icon={<Icon name="users" size={22} />}
          accessibilityLabel={strings.friends.open}
          onPress={() => {
            onClose({animated: false});
            navigate('/freunde');
          }}
          variant="surface"
          testID="drawer.friends"
        />
        <NotificationBell
          unread={unread}
          onPress={() => {
            onClose({animated: false});
            navigate('/benachrichtigungen');
          }}
          testID="drawer.notifications"
        />
        <CloseButton onClose={onClose} />
      </View>
      <FestSaison
        favorites={favorites.data?.items}
        loading={favorites.isPending}
        error={favorites.isError}
        today={todayInBerlin()}
        onOpen={eventId => {
          onClose({animated: false});
          navigate(`/f/${eventId}`);
        }}
        onDiscover={() => onClose()}
        onRetry={() => void favorites.refetch()}
      />
    </>
  );
}

const styles = StyleSheet.create({
  closeRow: {alignItems: 'flex-end'},
  timeline: {gap: 18, opacity: 0.5, marginVertical: 8},
  timelineItem: {flexDirection: 'row', gap: 14, alignItems: 'flex-start'},
  timelineText: {flex: 1, gap: 8},
  dot: {width: 12, height: 12, borderRadius: 6, borderWidth: 2, marginTop: 2},
  center: {textAlign: 'center'},
  userRow: {flexDirection: 'row', alignItems: 'center', gap: 8},
  user: {flex: 1, flexDirection: 'row', alignItems: 'center', gap: 12},
  userText: {flex: 1},
  footer: {gap: 4},
});
