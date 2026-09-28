import React, {ReactNode} from 'react';
import {Pressable} from 'react-native';

import {MIN_TOUCH_TARGET, useTheme} from '@/theme';

export interface IconButtonProps {
  /** Icon element (e.g. an SVG icon). */
  icon: ReactNode;
  /** Required for screen readers, e.g. "Zurück". */
  accessibilityLabel: string;
  onPress: () => void;
  testID: string;
  /** `glass` for buttons floating over images, `surface` elsewhere. */
  variant?: 'glass' | 'surface';
  size?: number;
  disabled?: boolean;
}

/** Round icon button (44 pt by default). */
export function IconButton({
  icon,
  accessibilityLabel,
  onPress,
  testID,
  variant = 'glass',
  size = MIN_TOUCH_TARGET,
  disabled = false,
}: IconButtonProps) {
  const theme = useTheme();
  return (
    <Pressable
      testID={testID}
      accessibilityRole="button"
      accessibilityLabel={accessibilityLabel}
      accessibilityState={{disabled}}
      disabled={disabled}
      onPress={onPress}
      hitSlop={Math.max(0, (MIN_TOUCH_TARGET - size) / 2)}
      style={({pressed}) => ({
        width: size,
        height: size,
        borderRadius: size / 2,
        alignItems: 'center',
        justifyContent: 'center',
        backgroundColor:
          variant === 'glass'
            ? theme.colors.glass
            : theme.colors.surfaceVariant,
        opacity: disabled ? 0.45 : pressed ? 0.8 : 1,
      })}
    >
      {icon}
    </Pressable>
  );
}
