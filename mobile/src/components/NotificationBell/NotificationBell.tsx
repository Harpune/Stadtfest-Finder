import React from 'react';
import {StyleSheet, View} from 'react-native';

import {strings} from '@/strings/de';
import {useTheme} from '@/theme';

import {Icon} from '../Icon/Icon';
import {IconButton} from '../IconButton/IconButton';
import {Text} from '../Text/Text';

export interface NotificationBellProps {
  /** Unread notifications; the pink counter is hidden at 0. */
  unread: number;
  onPress: () => void;
  testID: string;
}

/** Bell next to the user in the profile drawer, with the pink unread counter (R11). */
export function NotificationBell({
  unread,
  onPress,
  testID,
}: NotificationBellProps) {
  const theme = useTheme();
  const c = theme.colors;
  const label =
    unread > 0
      ? strings.notifications.bellUnread(unread)
      : strings.notifications.title;
  return (
    <View>
      <IconButton
        icon={<Icon name="bell" size={22} />}
        accessibilityLabel={label}
        onPress={onPress}
        variant="surface"
        testID={testID}
      />
      {unread > 0 ? (
        <View
          testID={`${testID}.badge`}
          pointerEvents="none"
          style={[
            styles.badge,
            {backgroundColor: c.secondary, borderColor: c.background},
          ]}
        >
          <Text
            variant="caption"
            style={[styles.count, {color: c.onSecondary}]}
          >
            {unread > 99 ? '99+' : unread}
          </Text>
        </View>
      ) : null}
    </View>
  );
}

const styles = StyleSheet.create({
  badge: {
    position: 'absolute',
    top: -4,
    right: -4,
    minWidth: 20,
    height: 20,
    borderRadius: 10,
    borderWidth: 2,
    paddingHorizontal: 4,
    alignItems: 'center',
    justifyContent: 'center',
  },
  count: {fontSize: 11, lineHeight: 14, fontWeight: '700'},
});
