import React from 'react';
import {StyleSheet, View} from 'react-native';

import type {EventStatusTone} from '@/features/events/status';
import {useTheme} from '@/theme';

import {Text} from '../Text/Text';

export interface CategoryPillProps {
  emoji: string;
  name: string;
  testID?: string;
}

/** Category pill of the detail header: emoji and name on surface2. */
export function CategoryPill({emoji, name, testID}: CategoryPillProps) {
  const theme = useTheme();
  return (
    <View
      testID={testID}
      style={[
        styles.pill,
        {
          backgroundColor: theme.colors.surfaceVariant,
          borderRadius: theme.radius.chip,
        },
      ]}
    >
      <Text style={styles.emoji}>{emoji}</Text>
      <Text variant="bodyStrong" style={styles.label}>
        {name}
      </Text>
    </View>
  );
}

export interface StatusPillProps {
  label: string;
  tone: EventStatusTone;
  testID?: string;
}

/**
 * Status pill: running = amber on amber-soft with dot, soon/cancelled = rose on rose-soft,
 * otherwise muted on surface2 (R04-US4: "Abgesagt" red on roseSoft).
 */
export function StatusPill({label, tone, testID}: StatusPillProps) {
  const theme = useTheme();
  const c = theme.colors;
  const [background, foreground] =
    tone === 'running'
      ? [c.primaryContainer, c.primaryText]
      : tone === 'soon' || tone === 'cancelled'
        ? [c.secondaryContainer, c.secondaryText]
        : [c.surfaceVariant, c.onSurfaceMuted];
  return (
    <View
      testID={testID}
      style={[
        styles.pill,
        {backgroundColor: background, borderRadius: theme.radius.chip},
      ]}
    >
      {tone === 'running' ? (
        <View style={[styles.dot, {backgroundColor: c.primary}]} />
      ) : null}
      <Text variant="bodyStrong" style={[styles.label, {color: foreground}]}>
        {label}
      </Text>
    </View>
  );
}

const styles = StyleSheet.create({
  pill: {
    flexDirection: 'row',
    alignItems: 'center',
    gap: 6,
    paddingHorizontal: 12,
    height: 36,
    alignSelf: 'flex-start',
  },
  emoji: {fontSize: 15},
  label: {fontSize: 14},
  dot: {width: 10, height: 10, borderRadius: 5},
});
