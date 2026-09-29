import React from 'react';
import {Pressable, StyleSheet, View} from 'react-native';

import {strings} from '@/strings/de';
import {MIN_TOUCH_TARGET, useTheme} from '@/theme';

import {Icon} from '../Icon/Icon';
import {Text} from '../Text/Text';

export interface FilterButtonProps {
  /** Number of active filters; shown as a rose badge when > 0. */
  activeCount: number;
  onPress: () => void;
  testID: string;
}

/** 40 × 40 filter button inside the search field (R03-US7). */
export function FilterButton({
  activeCount,
  onPress,
  testID,
}: FilterButtonProps) {
  const theme = useTheme();
  const label =
    activeCount > 0
      ? `${strings.discover.openFilter}, ${strings.discover.activeFilters(activeCount)}`
      : strings.discover.openFilter;
  return (
    <Pressable
      testID={testID}
      accessibilityRole="button"
      accessibilityLabel={label}
      onPress={onPress}
      hitSlop={(MIN_TOUCH_TARGET - 40) / 2}
      style={({pressed}) => [styles.button, {opacity: pressed ? 0.7 : 1}]}
    >
      <Icon name="sliders" size={22} />
      {activeCount > 0 ? (
        <View
          testID={`${testID}.badge`}
          style={[styles.badge, {backgroundColor: theme.colors.secondary}]}
        >
          <Text
            variant="micro"
            style={{color: theme.colors.onSecondary, fontSize: 10}}
          >
            {activeCount}
          </Text>
        </View>
      ) : null}
    </Pressable>
  );
}

const styles = StyleSheet.create({
  button: {
    width: 40,
    height: 40,
    alignItems: 'center',
    justifyContent: 'center',
  },
  badge: {
    position: 'absolute',
    top: 2,
    right: 0,
    minWidth: 17,
    height: 17,
    borderRadius: 9,
    paddingHorizontal: 4,
    alignItems: 'center',
    justifyContent: 'center',
  },
});
