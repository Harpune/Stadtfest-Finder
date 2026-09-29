import React from 'react';
import {StyleSheet, View} from 'react-native';

import type {EventStatusTone} from '@/features/events/status';
import {useTheme} from '@/theme';

import {Text} from '../Text/Text';

export interface StatusTextProps {
  label: string;
  tone: EventStatusTone;
}

/** Status line: running = amber with dot, soon/cancelled = rose, otherwise muted. */
export function StatusText({label, tone}: StatusTextProps) {
  const theme = useTheme();
  const c = theme.colors;
  const color =
    tone === 'running'
      ? c.primaryText
      : tone === 'soon' || tone === 'cancelled'
        ? c.secondaryText
        : c.onSurfaceMuted;
  return (
    <View style={styles.row}>
      {tone === 'running' ? (
        <View style={[styles.dot, {backgroundColor: c.primary}]} />
      ) : null}
      <Text variant="meta" style={{color, fontFamily: theme.fonts.semibold}}>
        {label}
      </Text>
    </View>
  );
}

const styles = StyleSheet.create({
  row: {flexDirection: 'row', alignItems: 'center', gap: 5},
  dot: {width: 9, height: 9, borderRadius: 5},
});
