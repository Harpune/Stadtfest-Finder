/**
 * Start screen. Placeholder until R03 replaces it with the map ("Entdecken").
 */
import {Redirect} from 'expo-router';
import React from 'react';
import {StyleSheet, View} from 'react-native';
import {useSafeAreaInsets} from 'react-native-safe-area-context';

import {Button, Text, useToast} from '@/components';
import {strings} from '@/strings/de';
import {useTheme} from '@/theme';

const STORYBOOK_ENABLED = process.env.EXPO_PUBLIC_STORYBOOK_ENABLED === 'true';

export default function StartScreen() {
  const theme = useTheme();
  const insets = useSafeAreaInsets();
  const toast = useToast();

  if (STORYBOOK_ENABLED) {
    return <Redirect href="/storybook" />;
  }

  return (
    <View
      testID="start.screen"
      style={[
        styles.container,
        {backgroundColor: theme.colors.background, paddingTop: insets.top + 52},
      ]}
    >
      <Text variant="displayXL" testID="start.title">
        {strings.app.name}
      </Text>
      <Text variant="body" tone="muted">
        {strings.app.tagline}
      </Text>
      <Button
        label="Feste entdecken"
        testID="start.discover"
        onPress={() => toast(strings.app.comingSoon)}
        style={styles.button}
      />
    </View>
  );
}

const styles = StyleSheet.create({
  container: {flex: 1, paddingHorizontal: 16, gap: 12},
  button: {marginTop: 12},
});
