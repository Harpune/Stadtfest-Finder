import React from 'react';
import {StyleSheet, View} from 'react-native';

import {useTheme} from '@/theme';

import {Icon, IconName} from '../Icon/Icon';
import {Skeleton} from '../Skeleton/Skeleton';
import {Text} from '../Text/Text';

export interface InfoRow {
  icon: IconName;
  label: string;
  /** One entry per line (e.g. opening hours). */
  lines: readonly string[];
}

export interface InfoBlockProps {
  rows: readonly InfoRow[];
  loading?: boolean;
  testID?: string;
}

/** Info block (surface, radius 20): rows with icon tile 36 in amber-soft, label and value. */
export function InfoBlock({rows, loading = false, testID}: InfoBlockProps) {
  const theme = useTheme();
  const c = theme.colors;
  return (
    <View
      testID={testID}
      style={[
        styles.block,
        {backgroundColor: c.surface, borderRadius: theme.radius.block},
      ]}
    >
      {rows.map((row, i) => (
        <View
          key={row.label}
          style={[
            styles.row,
            i > 0 ? {borderTopWidth: 1, borderTopColor: c.outline} : null,
          ]}
        >
          <View style={[styles.tile, {backgroundColor: c.primaryContainer}]}>
            <Icon name={row.icon} size={19} color={c.primaryText} />
          </View>
          <View style={styles.text}>
            <Text variant="meta" tone="muted">
              {row.label}
            </Text>
            {row.lines.map(line => (
              <Text key={line} variant="bodyStrong" style={styles.value}>
                {line}
              </Text>
            ))}
          </View>
        </View>
      ))}
      {loading ? (
        <View
          style={[styles.row, {borderTopWidth: 1, borderTopColor: c.outline}]}
        >
          <Skeleton width={36} height={36} radius={10} />
          <View style={[styles.text, {gap: 8}]}>
            <Skeleton width={90} height={11} />
            <Skeleton width={200} height={15} />
          </View>
        </View>
      ) : null}
    </View>
  );
}

const styles = StyleSheet.create({
  block: {paddingHorizontal: 16},
  row: {
    flexDirection: 'row',
    gap: 14,
    paddingVertical: 14,
    alignItems: 'flex-start',
  },
  tile: {
    width: 36,
    height: 36,
    borderRadius: 10,
    alignItems: 'center',
    justifyContent: 'center',
  },
  text: {flex: 1, gap: 2},
  value: {fontSize: 16},
});
