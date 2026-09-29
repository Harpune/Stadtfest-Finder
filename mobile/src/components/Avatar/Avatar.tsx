import React from 'react';
import {StyleSheet, View} from 'react-native';

import {useTheme} from '@/theme';

import {Icon} from '../Icon/Icon';
import {Text} from '../Text/Text';

export interface AvatarProps {
  /** Initials, e.g. "LH"; without them a person icon is shown. */
  initials?: string;
  size?: number;
  testID?: string;
}

/** Round avatar with initials (drawer user row, account page). */
export function Avatar({initials, size = 32, testID}: AvatarProps) {
  const theme = useTheme();
  return (
    <View
      testID={testID}
      style={[
        styles.circle,
        {
          width: size,
          height: size,
          borderRadius: size / 2,
          backgroundColor: theme.colors.surfaceVariant,
        },
      ]}
    >
      {initials ? (
        <Text
          variant={size >= 40 ? 'bodyStrong' : 'meta'}
          style={{color: theme.colors.onSurface}}
        >
          {initials}
        </Text>
      ) : (
        <Icon name="user" size={size * 0.55} />
      )}
    </View>
  );
}

const styles = StyleSheet.create({
  circle: {alignItems: 'center', justifyContent: 'center'},
});
