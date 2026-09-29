import React from 'react';
import {Pressable, StyleSheet, View} from 'react-native';

import {useTheme} from '@/theme';

import {Icon, IconName} from '../Icon/Icon';
import {Text} from '../Text/Text';

export interface LinkRowProps {
  icon: IconName;
  label: string;
  /** Short value on the right, e.g. the host "oktoberfest.de". */
  value?: string;
  onPress: () => void;
  testID: string;
}

/** Tappable row on surface with icon, label and an amber value with ↗. */
export function LinkRow({icon, label, value, onPress, testID}: LinkRowProps) {
  const theme = useTheme();
  const c = theme.colors;
  return (
    <Pressable
      testID={testID}
      accessibilityRole="link"
      accessibilityLabel={value ? `${label}, ${value}` : label}
      onPress={onPress}
      style={({pressed}) => [
        styles.row,
        {
          backgroundColor: c.surface,
          borderRadius: theme.radius.block,
          opacity: pressed ? 0.8 : 1,
        },
      ]}
    >
      <Icon name={icon} size={22} color={c.primaryText} />
      <Text variant="bodyStrong" style={styles.label}>
        {label}
      </Text>
      {value ? (
        <View style={styles.value}>
          <Text variant="meta" tone="primary" numberOfLines={1}>
            {value}
          </Text>
          <Icon name="arrowUpRight" size={15} color={c.primaryText} />
        </View>
      ) : null}
    </Pressable>
  );
}

const styles = StyleSheet.create({
  row: {
    flexDirection: 'row',
    alignItems: 'center',
    gap: 14,
    paddingHorizontal: 18,
    height: 56,
  },
  label: {flex: 1, fontSize: 16},
  value: {flexDirection: 'row', alignItems: 'center', gap: 4, maxWidth: '50%'},
});
