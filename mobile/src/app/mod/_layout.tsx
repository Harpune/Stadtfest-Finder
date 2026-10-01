/**
 * Moderation view (R07-US1): fixed banner on top, events and categories as tabs at the
 * bottom, screens in between. Only for moderators; everyone else is sent to the map.
 */
import {Redirect, Stack} from 'expo-router';
import React from 'react';
import {StyleSheet, View} from 'react-native';
import {useSafeAreaInsets} from 'react-native-safe-area-context';

import {ModBanner, ModTabBar, useToast} from '@/components';
import {useAuth} from '@/features/auth/AuthProvider';
import {useExitModeration} from '@/features/moderation/useModeration';
import {strings} from '@/strings/de';
import {useTheme} from '@/theme';

const TABS = [
  {key: 'events', label: strings.mod.tabEvents, emoji: '📅'},
  {key: 'categories', label: strings.mod.tabCategories, emoji: '🏷️'},
] as const;

export default function ModerationLayout() {
  const theme = useTheme();
  const insets = useSafeAreaInsets();
  const {user, isModerator, status} = useAuth();
  const exit = useExitModeration();
  const toast = useToast();

  if (status !== 'restoring' && !isModerator) return <Redirect href="/" />;

  const name = user ? `${user.firstName} ${user.lastName}`.trim() : '';
  const region = user?.region?.name ?? '';

  return (
    <View style={[styles.root, {backgroundColor: theme.colors.background}]}>
      <ModBanner
        subtitle={strings.mod.bannerSubtitle(region, name)}
        onExit={() => exit()}
        topInset={insets.top}
        testID="mod.banner"
      />
      <View style={styles.content}>
        <Stack
          screenOptions={{
            headerShown: false,
            contentStyle: {backgroundColor: theme.colors.background},
            animation: 'slide_from_right',
          }}
        />
      </View>
      <ModTabBar
        tabs={TABS}
        active="events"
        onSelect={key => {
          // The categories tab follows in R09.
          if (key === 'categories') toast(strings.mod.categoriesSoon);
        }}
        bottomInset={insets.bottom}
        testID="mod.tabs"
      />
    </View>
  );
}

const styles = StyleSheet.create({
  root: {flex: 1},
  content: {flex: 1},
});
