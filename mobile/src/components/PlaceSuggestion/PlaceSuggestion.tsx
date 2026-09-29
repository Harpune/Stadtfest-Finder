import React from 'react';
import {Pressable, StyleSheet} from 'react-native';

import {useTheme} from '@/theme';

import {Icon} from '../Icon/Icon';
import {Text} from '../Text/Text';

export interface PlaceSuggestionProps {
  /** Complete label, e.g. "Zu 89073 Ulm springen". */
  label: string;
  onPress: () => void;
  testID: string;
}

/** Suggestion under the search field that moves the map to a place (R03-US5). */
export function PlaceSuggestion({
  label,
  onPress,
  testID,
}: PlaceSuggestionProps) {
  const theme = useTheme();
  const c = theme.colors;
  return (
    <Pressable
      testID={testID}
      accessibilityRole="button"
      accessibilityLabel={label}
      onPress={onPress}
      style={({pressed}) => [
        styles.row,
        theme.shadow.floating,
        {
          backgroundColor: c.floating,
          borderColor: c.outline,
          borderRadius: theme.radius.input,
          opacity: pressed ? 0.8 : 1,
        },
      ]}
    >
      <Icon name="navigation" size={18} color={c.primary} />
      <Text variant="bodyStrong" numberOfLines={1} style={styles.label}>
        {label}
      </Text>
    </Pressable>
  );
}

const styles = StyleSheet.create({
  row: {
    flexDirection: 'row',
    alignItems: 'center',
    gap: 10,
    height: 44,
    paddingHorizontal: 16,
    borderWidth: 1,
    alignSelf: 'flex-start',
    maxWidth: '100%',
  },
  label: {flexShrink: 1, fontSize: 15},
});
