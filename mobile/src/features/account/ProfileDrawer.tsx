/**
 * Profile drawer, basic version (R05-US5): guest variant (03-07) with login, signed-in
 * variant with user row and "Abmelden". The timeline follows in R06.
 */
import {router} from 'expo-router';
import React, {useEffect, useState} from 'react';
import {Pressable, StyleSheet, View} from 'react-native';

import {
  Avatar,
  Button,
  Icon,
  IconButton,
  SideDrawer,
  Skeleton,
  Text,
} from '@/components';
import {initialsOf, useAuth} from '@/features/auth/AuthProvider';
import {strings} from '@/strings/de';
import {useTheme} from '@/theme';

import {NameSheet} from './NameSheet';

export interface ProfileDrawerProps {
  visible: boolean;
  onClose: () => void;
}

export function ProfileDrawer({visible, onClose}: ProfileDrawerProps) {
  const {status, user, logout} = useAuth();
  const signedIn = status === 'signedIn';
  const [askName, setAskName] = useState(false);

  // First opening without a name (Apple without name sharing): ask for it once.
  const needsName = signedIn && user !== null && user.firstName === '';
  useEffect(() => {
    if (visible && needsName) setAskName(true);
  }, [visible, needsName]);

  const footer = signedIn ? (
    <Pressable
      testID="drawer.logout"
      accessibilityRole="button"
      onPress={async () => {
        onClose();
        await logout();
      }}
      style={styles.footerRow}
    >
      <Text variant="bodyStrong" tone="secondary">
        {strings.drawer.logout}
      </Text>
    </Pressable>
  ) : undefined;

  return (
    <>
      <SideDrawer
        visible={visible}
        onClose={onClose}
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

function CloseButton({onClose}: {onClose: () => void}) {
  return (
    <IconButton
      icon={<Icon name="close" size={22} />}
      accessibilityLabel={strings.common.close}
      onPress={onClose}
      variant="surface"
      testID="drawer.close"
    />
  );
}

function GuestContent({onClose}: {onClose: () => void}) {
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
          onClose();
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

function SignedInContent({onClose}: {onClose: () => void}) {
  const {user, email} = useAuth();
  const name = user ? `${user.firstName} ${user.lastName}`.trim() : '';
  return (
    <>
      <View style={styles.userRow}>
        <Pressable
          testID="drawer.user"
          accessibilityRole="button"
          accessibilityLabel={strings.drawer.openAccount}
          onPress={() => {
            onClose();
            router.push('/konto');
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
        <CloseButton onClose={onClose} />
      </View>
      <Text variant="displayL">{strings.drawer.title}</Text>
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
  footerRow: {paddingVertical: 14},
});
