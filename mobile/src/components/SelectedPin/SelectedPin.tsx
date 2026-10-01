import React from 'react';
import {StyleSheet, View} from 'react-native';

import {useTheme} from '@/theme';

import {Text} from '../Text/Text';

export interface SelectedPinProps {
  /** Short name of the event. */
  label: string;
  /** Date range below the name, e.g. "3.–4. Okt". */
  dateLabel: string;
  emoji: string;
  /** Which side the emoji bubble sits on; the pill extends to the other side. */
  align: 'left' | 'right';
  testID?: string;
}

/**
 * Selected marker: amber pill with short name and date, and the emoji bubble at the marker
 * position. It lies in its own layer and is never clustered (R03-US2). A second tap on it
 * opens the detail page.
 */
export function SelectedPin({
  label,
  dateLabel,
  emoji,
  align,
  testID,
}: SelectedPinProps) {
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
      <View style={styles.text}>
        <Text
          variant="bodyStrong"
          numberOfLines={1}
          style={[styles.label, {color: c.onPrimary}]}
        >
          {label}
        </Text>
        <Text
          variant="meta"
          numberOfLines={1}
          style={{color: c.onPrimary, fontFamily: theme.fonts.medium}}
        >
          {dateLabel}
        </Text>
      </View>
      {bubble}
    </View>
  );
}

const styles = StyleSheet.create({
  pill: {
    height: 56,
    borderRadius: 28,
    alignItems: 'center',
    paddingHorizontal: 6,
    gap: 8,
    maxWidth: 280,
    shadowOpacity: 0.55,
    shadowRadius: 14,
    shadowOffset: {width: 0, height: 0},
    elevation: 10,
  },
  text: {paddingHorizontal: 10, flexShrink: 1},
  label: {fontSize: 16, lineHeight: 20},
  bubble: {
    width: 44,
    height: 44,
    borderRadius: 22,
    alignItems: 'center',
    justifyContent: 'center',
  },
  emoji: {fontSize: 20, lineHeight: 24},
});
