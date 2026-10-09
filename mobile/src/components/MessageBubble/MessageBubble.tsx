import React from 'react';
import {StyleSheet, View} from 'react-native';

import {useTheme} from '@/theme';

import {Text} from '../Text/Text';

export interface MessageBubbleProps {
  /** User free text; shown in German quotation marks. */
  message: string;
  testID?: string;
}

/** The host's message as a speech bubble (06-01, 06-03); flat bottom-left corner. */
export function MessageBubble({message, testID}: MessageBubbleProps) {
  const theme = useTheme();
  const radius = theme.radius.block;
  return (
    <View
      testID={testID}
      style={[
        styles.bubble,
        {
          backgroundColor: theme.colors.surface,
          borderRadius: radius,
          borderBottomLeftRadius: 6,
        },
      ]}
    >
      <Text variant="body">{`„${message}“`}</Text>
    </View>
  );
}

const styles = StyleSheet.create({
  bubble: {paddingHorizontal: 16, paddingVertical: 14},
});
