import React from 'react';
import {StyleSheet, View} from 'react-native';

import {useTheme} from '@/theme';

import {Text} from '../Text/Text';

export interface ProgramEntry {
  key: string;
  weekday: string; // "SA"
  day: string; // "19.9."
  title: string;
  /** "10:45 Uhr · danach Anstich um 12 Uhr" */
  subtitle?: string;
}

export interface ProgramListProps {
  entries: readonly ProgramEntry[];
  testID?: string;
}

/** Program rows: weekday + date in rose, title and subtitle. */
export function ProgramList({entries, testID}: ProgramListProps) {
  const theme = useTheme();
  const c = theme.colors;
  return (
    <View testID={testID} style={styles.list}>
      {entries.map(entry => (
        <View
          key={entry.key}
          style={[
            styles.row,
            {backgroundColor: c.surface, borderRadius: theme.radius.block},
          ]}
        >
          <View style={styles.date}>
            <Text variant="caption" tone="muted" style={styles.weekday}>
              {entry.weekday}
            </Text>
            <Text
              variant="bodyStrong"
              style={[styles.day, {color: c.secondaryText}]}
            >
              {entry.day}
            </Text>
          </View>
          <View style={styles.text}>
            <Text variant="bodyStrong" style={styles.title}>
              {entry.title}
            </Text>
            {entry.subtitle ? (
              <Text variant="meta" tone="muted">
                {entry.subtitle}
              </Text>
            ) : null}
          </View>
        </View>
      ))}
    </View>
  );
}

const styles = StyleSheet.create({
  list: {gap: 10},
  row: {flexDirection: 'row', alignItems: 'center', padding: 14, gap: 14},
  date: {width: 56, alignItems: 'center'},
  weekday: {fontFamily: 'Outfit_600SemiBold', letterSpacing: 0.5},
  day: {fontSize: 18},
  text: {flex: 1, gap: 2},
  title: {fontSize: 16},
});
