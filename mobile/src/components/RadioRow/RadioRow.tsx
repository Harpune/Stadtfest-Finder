import React from 'react';
import {Pressable, StyleSheet, View} from 'react-native';

import {useTheme} from '@/theme';

import {Text} from '../Text/Text';

export interface RadioRowProps {
  label: string;
  emoji?: string;
  selected: boolean;
  onPress: () => void;
  disabled?: boolean;
  testID: string;
}

/** Choice in a list of options (e.g. replacement category, 10-04). */
export function RadioRow({
  label,
  emoji,
  selected,
  onPress,
  disabled = false,
  testID,
}: RadioRowProps) {
  const theme = useTheme();
  const c = theme.colors;
  return (
    <Pressable
      testID={testID}
      accessibilityRole="radio"
      accessibilityLabel={label}
      accessibilityState={{selected, disabled}}
      disabled={disabled}
      onPress={onPress}
      style={({pressed}) => [
        styles.row,
        {
          backgroundColor: c.surface,
          borderColor: selected ? c.mod.primary : c.outline,
          borderRadius: theme.radius.input,
          opacity: pressed ? 0.85 : 1,
        },
      ]}
    >
      {emoji ? <Text style={styles.emoji}>{emoji}</Text> : null}
      <Text variant="bodyStrong" style={styles.label} numberOfLines={1}>
        {label}
      </Text>
      <View
        style={[
          styles.radio,
          {borderColor: selected ? c.mod.primary : c.onSurfaceFaint},
        ]}
      >
        {selected ? (
          <View style={[styles.dot, {backgroundColor: c.mod.primary}]} />
        ) : null}
      </View>
    </Pressable>
  );
}

const styles = StyleSheet.create({
  row: {
    minHeight: 52,
    flexDirection: 'row',
    alignItems: 'center',
    gap: 12,
    paddingHorizontal: 14,
    borderWidth: 1.5,
  },
  emoji: {fontSize: 20, lineHeight: 26},
  label: {flex: 1, fontSize: 16},
  radio: {
    width: 22,
    height: 22,
    borderRadius: 11,
    borderWidth: 2,
    alignItems: 'center',
    justifyContent: 'center',
  },
  dot: {width: 10, height: 10, borderRadius: 5},
});
