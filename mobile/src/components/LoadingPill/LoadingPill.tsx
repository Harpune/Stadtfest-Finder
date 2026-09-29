import React from 'react';
import {StyleSheet, View} from 'react-native';

import {useTheme} from '@/theme';

import {Spinner} from '../Spinner/Spinner';
import {Text} from '../Text/Text';

export interface LoadingPillProps {
  label: string;
  /** Spinner for loading; without it the pill is a quiet hint (e.g. offline). */
  spinner?: boolean;
  testID?: string;
}

/** Floating pill over the map, e.g. "Feste werden geladen …" (screen 01-02). */
export function LoadingPill({label, spinner = true, testID}: LoadingPillProps) {
  const theme = useTheme();
  return (
    <View
      testID={testID}
      accessibilityRole={spinner ? 'progressbar' : 'text'}
      accessibilityLiveRegion="polite"
      style={[
        styles.pill,
        theme.shadow.floating,
        {
          backgroundColor: theme.colors.floating,
          borderColor: theme.colors.outline,
        },
      ]}
    >
      {spinner ? <Spinner color={theme.colors.primary} /> : null}
      <Text variant="meta" style={{fontFamily: theme.fonts.medium}}>
        {label}
      </Text>
    </View>
  );
}

const styles = StyleSheet.create({
  pill: {
    flexDirection: 'row',
    alignItems: 'center',
    gap: 8,
    height: 38,
    paddingHorizontal: 16,
    borderRadius: 19,
    borderWidth: 1,
    alignSelf: 'center',
  },
});
