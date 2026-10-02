import React, {ReactNode} from 'react';
import {Pressable, StyleSheet, View} from 'react-native';

import {useTheme} from '@/theme';

import {Icon} from '../Icon/Icon';
import {Text} from '../Text/Text';

export interface ModCategoryRowProps {
  name: string;
  emoji: string;
  /** Category color: border of the emoji circle (like the map marker). */
  color: string;
  /** "3 Feste" or "Deaktiviert · 0 Feste". */
  meta: string;
  /** Inactive categories are shown at half opacity (10-01). */
  inactive?: boolean;
  /** Drag grip from `SortableList`; missing in read-only mode. */
  handle?: ReactNode;
  onPress: () => void;
  testID: string;
}

/** Row of the category overview (10-01): grip, emoji circle, name, count, chevron. */
export function ModCategoryRow({
  name,
  emoji,
  color,
  meta,
  inactive = false,
  handle,
  onPress,
  testID,
}: ModCategoryRowProps) {
  const theme = useTheme();
  const c = theme.colors;
  return (
    <Pressable
      testID={testID}
      accessibilityRole="button"
      accessibilityLabel={`${name}, ${meta}`}
      onPress={onPress}
      style={({pressed}) => [
        styles.row,
        {
          backgroundColor: c.surface,
          borderColor: c.outline,
          borderRadius: theme.radius.block,
          opacity: pressed ? 0.85 : 1,
        },
      ]}
    >
      {handle ?? <View style={styles.noHandle} />}
      <View style={[styles.content, inactive && styles.inactive]}>
        <View
          style={[
            styles.circle,
            {borderColor: color, backgroundColor: c.surfaceVariant},
          ]}
        >
          <Text style={styles.emoji}>{emoji}</Text>
        </View>
        <View style={styles.text}>
          <Text variant="bodyStrong" style={styles.name} numberOfLines={1}>
            {name}
          </Text>
          <Text variant="body" tone="muted" numberOfLines={1}>
            {meta}
          </Text>
        </View>
        <Icon name="chevronRight" size={18} color={c.onSurfaceFaint} />
      </View>
    </Pressable>
  );
}

const styles = StyleSheet.create({
  row: {
    flex: 1,
    flexDirection: 'row',
    alignItems: 'center',
    borderWidth: 1,
    paddingLeft: 8,
    paddingRight: 16,
  },
  noHandle: {width: 8},
  content: {flex: 1, flexDirection: 'row', alignItems: 'center', gap: 14},
  inactive: {opacity: 0.5},
  circle: {
    width: 44,
    height: 44,
    borderRadius: 22,
    borderWidth: 2,
    alignItems: 'center',
    justifyContent: 'center',
  },
  emoji: {fontSize: 20, lineHeight: 26},
  text: {flex: 1, gap: 2},
  name: {fontSize: 17},
});
