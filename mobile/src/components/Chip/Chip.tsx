import React from 'react';
import {Pressable, StyleSheet} from 'react-native';

import {useTheme} from '@/theme';

import {Icon} from '../Icon/Icon';
import {Text} from '../Text/Text';

export interface ChipProps {
  label: string;
  onPress: () => void;
  testID: string;
  active?: boolean;
  emoji?: string;
  /** Count shown after the label (category chips on the map). */
  count?: number;
  /** Shows ▾ (time chip that opens the filter sheet). */
  dropdown?: boolean;
  /** `floating` over the map (height 36), `sheet` inside sheets (height 42). */
  variant?: 'floating' | 'sheet';
  disabled?: boolean;
}

/** Filter chip. Active: amber background with dark text (#15111C) in both schemes. */
export function Chip({
  label,
  onPress,
  testID,
  active = false,
  emoji,
  count,
  dropdown = false,
  variant = 'floating',
  disabled = false,
}: ChipProps) {
  const theme = useTheme();
  const c = theme.colors;
  const foreground = active ? c.onPrimary : c.onSurface;
  const background = active
    ? c.primary
    : variant === 'floating'
      ? c.floating
      : c.surfaceVariant;
  return (
    <Pressable
      testID={testID}
      accessibilityRole="button"
      accessibilityState={{selected: active, disabled}}
      accessibilityLabel={count !== undefined ? `${label}, ${count}` : label}
      disabled={disabled}
      onPress={onPress}
      style={({pressed}) => [
        styles.chip,
        variant === 'floating' && !active ? theme.shadow.floating : null,
        {
          height: variant === 'floating' ? 38 : 42,
          borderRadius: variant === 'floating' ? theme.radius.chip : 14,
          backgroundColor: background,
          borderColor: active
            ? c.primary
            : variant === 'floating'
              ? c.outline
              : background,
          opacity: disabled ? 0.45 : pressed ? 0.8 : 1,
        },
      ]}
    >
      {emoji ? <Text style={styles.emoji}>{emoji}</Text> : null}
      <Text variant="bodyStrong" style={{color: foreground, fontSize: 15}}>
        {label}
      </Text>
      {count !== undefined ? (
        <Text
          variant="body"
          style={{color: active ? c.onPrimary : c.onSurfaceMuted, fontSize: 15}}
        >
          {count}
        </Text>
      ) : null}
      {dropdown ? (
        <Icon
          name="chevronDown"
          size={14}
          color={foreground}
          strokeWidth={2.6}
        />
      ) : null}
    </Pressable>
  );
}

const styles = StyleSheet.create({
  chip: {
    flexDirection: 'row',
    alignItems: 'center',
    gap: 7,
    paddingHorizontal: 14,
    borderWidth: 1,
  },
  emoji: {fontSize: 16},
});
