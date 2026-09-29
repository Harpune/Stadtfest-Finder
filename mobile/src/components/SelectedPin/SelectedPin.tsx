import React from 'react';
import {StyleSheet, View} from 'react-native';

import {useTheme} from '@/theme';

import {Text} from '../Text/Text';

export interface SelectedPinProps {
  label: string;
  emoji: string;
  /** Which side the emoji bubble sits on; the pill extends to the other side. */
  align: 'left' | 'right';
  testID?: string;
}

/**
 * Selected marker: amber pill (height 44) with the short name and the emoji bubble at the
 * marker position. It lies in its own layer and is never clustered (R03-US2).
 */
export function SelectedPin({label, emoji, align, testID}: SelectedPinProps) {
  const theme = useTheme();
  const c = theme.colors;
  const bubble = (
    <View style={[styles.bubble, {backgroundColor: c.background}]}>
      <Text style={styles.emoji}>{emoji}</Text>
    </View>
  );
  return (
    <View
      testID={testID}
      style={[
        styles.pill,
        {
          backgroundColor: c.primary,
          flexDirection: align === 'right' ? 'row' : 'row-reverse',
          shadowColor: c.primary,
        },
      ]}
    >
      <Text
        variant="bodyStrong"
        numberOfLines={1}
        style={[styles.label, {color: c.onPrimary}]}
      >
        {label}
      </Text>
      {bubble}
    </View>
  );
}

const styles = StyleSheet.create({
  pill: {
    height: 44,
    borderRadius: 22,
    alignItems: 'center',
    paddingHorizontal: 4,
    gap: 8,
    maxWidth: 240,
    shadowOpacity: 0.55,
    shadowRadius: 14,
    shadowOffset: {width: 0, height: 0},
    elevation: 10,
  },
  label: {fontSize: 16, paddingHorizontal: 10, flexShrink: 1},
  bubble: {
    width: 36,
    height: 36,
    borderRadius: 18,
    alignItems: 'center',
    justifyContent: 'center',
  },
  emoji: {fontSize: 17, lineHeight: 21},
});
