import React from 'react';
import {StyleSheet, View} from 'react-native';

import {useTheme} from '@/theme';

import {Avatar} from '../Avatar/Avatar';
import {Text} from '../Text/Text';

export interface FriendRowProps {
  name: string;
  initials: string;
  /** Avatar color from the friend palette (deterministic per friend). */
  color: string;
  /** Second line, e.g. "Befreundet seit Okt 2026". */
  meta: string;
  testID: string;
}

/** Row of the friends list (R12): avatar 40 with initials, name and meta line. */
export function FriendRow({
  name,
  initials,
  color,
  meta,
  testID,
}: FriendRowProps) {
  const theme = useTheme();
  return (
    <View
      testID={testID}
      accessible
      accessibilityLabel={`${name}, ${meta}`}
      style={[
        styles.row,
        {
          backgroundColor: theme.colors.surface,
          borderRadius: theme.radius.block,
        },
      ]}
    >
      <Avatar initials={initials} color={color} size={40} />
      <View style={styles.text}>
        <Text variant="bodyStrong" numberOfLines={1}>
          {name}
        </Text>
        <Text variant="meta" tone="muted" numberOfLines={1}>
          {meta}
        </Text>
      </View>
    </View>
  );
}

const styles = StyleSheet.create({
  row: {flexDirection: 'row', alignItems: 'center', gap: 12, padding: 12},
  text: {flex: 1, gap: 2},
});
