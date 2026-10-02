import React from 'react';
import {Pressable, StyleProp, StyleSheet, View, ViewStyle} from 'react-native';

import {Theme, useTheme} from '@/theme';
import {strings} from '@/strings/de';

import {Spinner} from '../Spinner/Spinner';
import {Text} from '../Text/Text';

export type ButtonVariant =
  'primary' | 'secondary' | 'ghost' | 'danger' | 'destructive' | 'mod';
export type ButtonSize = 'large' | 'medium';

export interface ButtonProps {
  label: string;
  onPress: () => void;
  testID: string;
  variant?: ButtonVariant;
  size?: ButtonSize;
  loading?: boolean;
  disabled?: boolean;
  /** Label shown while loading, e.g. "Einen Moment …". */
  loadingLabel?: string;
  style?: StyleProp<ViewStyle>;
}

function colorsFor(theme: Theme, variant: ButtonVariant) {
  const c = theme.colors;
  switch (variant) {
    case 'primary':
      return {
        background: c.primary,
        foreground: c.onPrimary,
        border: c.primary,
      };
    case 'secondary':
      return {
        background: c.surfaceVariant,
        foreground: c.onSurface,
        border: c.surfaceVariant,
      };
    case 'ghost':
      return {
        background: 'transparent',
        foreground: c.onSurface,
        border: c.outline,
      };
    case 'danger':
      return {
        background: c.errorContainer,
        foreground: c.error,
        border: c.errorContainer,
      };
    case 'destructive':
      // Solid pink confirm button of destructive dialogs (08-09, 08-10).
      return {
        background: c.secondary,
        foreground: c.onSecondary,
        border: c.secondary,
      };
    case 'mod':
      return {
        background: c.mod.primary,
        foreground: c.mod.onPrimary,
        border: c.mod.primary,
      };
  }
}

/** Primary action button. Always pass a stable `testID` (Maestro, tests). */
export function Button({
  label,
  onPress,
  testID,
  variant = 'primary',
  size = 'large',
  loading = false,
  disabled = false,
  loadingLabel = strings.common.loading,
  style,
}: ButtonProps) {
  const theme = useTheme();
  const colors = colorsFor(theme, variant);
  const inactive = disabled || loading;

  return (
    <Pressable
      testID={testID}
      accessibilityRole="button"
      accessibilityLabel={label}
      accessibilityState={{disabled: inactive, busy: loading}}
      disabled={inactive}
      onPress={onPress}
      style={({pressed}) => [
        styles.base,
        {
          minHeight: size === 'large' ? 54 : 44,
          borderRadius:
            size === 'large' ? theme.radius.buttonLarge : theme.radius.button,
          backgroundColor: colors.background,
          borderColor: colors.border,
          opacity: disabled ? 0.45 : pressed ? 0.85 : 1,
        },
        style,
      ]}
    >
      <View style={styles.content}>
        {loading ? <Spinner color={colors.foreground} /> : null}
        <Text
          variant="bodyStrong"
          // Long labels wrap to a second line and the button grows (08-09).
          numberOfLines={2}
          style={[styles.label, {color: colors.foreground}]}
        >
          {loading ? loadingLabel : label}
        </Text>
      </View>
    </Pressable>
  );
}

const styles = StyleSheet.create({
  base: {
    borderWidth: 1,
    justifyContent: 'center',
    alignItems: 'center',
    paddingHorizontal: 18,
    paddingVertical: 6,
  },
  content: {
    flexDirection: 'row',
    alignItems: 'center',
    gap: 8,
    maxWidth: '100%',
  },
  label: {fontSize: 16, textAlign: 'center', flexShrink: 1},
});
