import React from 'react';
import {StyleSheet, View} from 'react-native';

import {useTheme} from '@/theme';

import {Text} from '../Text/Text';

export interface EventMarkerProps {
  emoji: string;
  /** Category color, used for the 2 px border. */
  color: string;
  testID?: string;
}

/** Map marker: 38 pt circle in surface2, 2 px category border, emoji 17 pt (R03-US2). */
export function EventMarker({emoji, color, testID}: EventMarkerProps) {
  const theme = useTheme();
  return (
    <View
      testID={testID}
      style={[
        styles.marker,
        theme.shadow.floating,
        {backgroundColor: theme.colors.surfaceVariant, borderColor: color},
      ]}
    >
      <Text style={styles.emoji}>{emoji}</Text>
    </View>
  );
}

const styles = StyleSheet.create({
  marker: {
    width: 38,
    height: 38,
    borderRadius: 19,
    borderWidth: 2,
    alignItems: 'center',
    justifyContent: 'center',
  },
  emoji: {fontSize: 17, lineHeight: 21},
});
