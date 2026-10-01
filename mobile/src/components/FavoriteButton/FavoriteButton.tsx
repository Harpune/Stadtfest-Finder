import React from 'react';

import {useTheme} from '@/theme';

import {Icon} from '../Icon/Icon';
import {IconButton} from '../IconButton/IconButton';

export interface FavoriteButtonProps {
  /** Filled pink heart when the event is a favorite (R06-US1). */
  active: boolean;
  /** Screen reader label, e.g. "Oktoberfest merken". */
  accessibilityLabel: string;
  onPress: () => void;
  testID: string;
  size?: number;
  iconSize?: number;
  disabled?: boolean;
}

/** Heart button on detail page and list cards: outline, or filled pink when active. */
export function FavoriteButton({
  active,
  accessibilityLabel,
  onPress,
  testID,
  size,
  iconSize = 21,
  disabled,
}: FavoriteButtonProps) {
  const theme = useTheme();
  const pink = theme.colors.secondary;
  return (
    <IconButton
      icon={
        <Icon
          name="heart"
          size={iconSize}
          color={active ? pink : undefined}
          fill={active ? pink : 'none'}
        />
      }
      accessibilityLabel={accessibilityLabel}
      onPress={onPress}
      testID={testID}
      size={size}
      disabled={disabled}
      selected={active}
    />
  );
}
