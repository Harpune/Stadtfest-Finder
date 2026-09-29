import React from 'react';
import {Pressable, StyleSheet, View} from 'react-native';

import {strings} from '@/strings/de';
import {useTheme} from '@/theme';

import {Icon} from '../Icon/Icon';
import {Text} from '../Text/Text';

export interface AvatarButtonProps {
  onPress: () => void;
  testID: string;
  /** Initials of the signed-in user; without them the guest icon is shown. */
  initials?: string;
  /** Rose dot for unread notifications. */
  hasUnread?: boolean;
  size?: number;
}

/** Profile button (50 pt, 2 px amber ring) next to the search field. */
export function AvatarButton({
  onPress,
  testID,
  initials,
  hasUnread = false,
  size = 50,
}: AvatarButtonProps) {
  const theme = useTheme();
  const c = theme.colors;
  return (
    <Pressable
      testID={testID}
      accessibilityRole="button"
      accessibilityLabel={strings.discover.profile}
      onPress={onPress}
      style={({pressed}) => [
        styles.ring,
        theme.shadow.floating,
        {
          width: size,
          height: size,
          borderRadius: size / 2,
          borderColor: c.primary,
          backgroundColor: initials ? '#4A3A5C' : c.floating,
          opacity: pressed ? 0.8 : 1,
        },
      ]}
    >
      {initials ? (
        <Text variant="bodyStrong" style={{color: '#F4EEF8'}}>
          {initials}
        </Text>
      ) : (
        <Icon name="user" size={24} />
      )}
      {hasUnread ? (
        <View
          testID={`${testID}.unread`}
          style={[
            styles.dot,
            {backgroundColor: c.secondary, borderColor: c.background},
          ]}
        />
      ) : null}
    </Pressable>
  );
}

const styles = StyleSheet.create({
  ring: {borderWidth: 2, alignItems: 'center', justifyContent: 'center'},
  dot: {
    position: 'absolute',
    top: 1,
    right: 1,
    width: 12,
    height: 12,
    borderRadius: 6,
    borderWidth: 2,
  },
});
