import React from 'react';
import {Pressable, StyleSheet, View} from 'react-native';

import {useTheme} from '@/theme';

import {Text} from '../Text/Text';

export interface NotificationRowProps {
  /** Emoji of the type, e.g. "⏰". */
  icon: string;
  /** Type line, e.g. "Erinnerung". */
  kind: string;
  text: string;
  /** Relative time, e.g. "vor 12 Min.". */
  time: string;
  unread: boolean;
  /** `alert` (pink icon tile and type line) for cancellations. */
  tone?: 'default' | 'alert';
  onPress: () => void;
  testID: string;
}

/**
 * Entry of the notification list (07-01): icon tile 40, type line, text and time. Unread
 * entries are bold on `surface` with a pink dot.
 */
export function NotificationRow({
  icon,
  kind,
  text,
  time,
  unread,
  tone = 'default',
  onPress,
  testID,
}: NotificationRowProps) {
  const theme = useTheme();
  const c = theme.colors;
  const alert = tone === 'alert';
  return (
    <Pressable
      testID={testID}
      accessibilityRole="button"
      accessibilityLabel={`${kind}. ${text}. ${time}`}
      accessibilityState={{selected: unread}}
      onPress={onPress}
      style={({pressed}) => [
        styles.row,
        {
          backgroundColor: unread ? c.surface : 'transparent',
          borderRadius: theme.radius.block,
          opacity: pressed ? 0.8 : 1,
        },
      ]}
    >
      <View
        style={[
          styles.tile,
          {backgroundColor: alert ? c.secondaryContainer : c.surfaceVariant},
        ]}
      >
        <Text style={styles.emoji}>{icon}</Text>
      </View>
      <View style={styles.text}>
        <Text
          variant="meta"
          style={{color: alert ? c.secondaryText : c.onSurfaceMuted}}
          numberOfLines={1}
        >
          {kind}
        </Text>
        <Text
          variant={unread ? 'bodyStrong' : 'body'}
          numberOfLines={3}
          testID={`${testID}.text`}
        >
          {text}
        </Text>
        <Text variant="caption" tone="muted">
          {time}
        </Text>
      </View>
      {unread ? (
        <View
          testID={`${testID}.unread`}
          style={[styles.dot, {backgroundColor: c.secondary}]}
        />
      ) : null}
    </Pressable>
  );
}

const styles = StyleSheet.create({
  row: {
    flexDirection: 'row',
    alignItems: 'flex-start',
    gap: 12,
    padding: 12,
  },
  tile: {
    width: 40,
    height: 40,
    borderRadius: 12,
    alignItems: 'center',
    justifyContent: 'center',
  },
  emoji: {fontSize: 18},
  text: {flex: 1, gap: 2},
  dot: {width: 8, height: 8, borderRadius: 4, marginTop: 6},
});
