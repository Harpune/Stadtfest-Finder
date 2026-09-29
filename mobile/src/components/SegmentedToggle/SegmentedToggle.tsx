import React from 'react';
import {Pressable, StyleSheet, View} from 'react-native';

import {useTheme} from '@/theme';

import {Icon, IconName} from '../Icon/Icon';
import {Text} from '../Text/Text';

export interface SegmentedToggleOption<T extends string> {
  value: T;
  label: string;
  icon: IconName;
}

export interface SegmentedToggleProps<T extends string> {
  options: readonly [SegmentedToggleOption<T>, SegmentedToggleOption<T>];
  value: T;
  onChange: (value: T) => void;
  testID: string;
}

/**
 * Map/list switch (radius 24, segments 40 high). Inverted colors: light pill with a dark
 * active segment in dark mode, dark pill with a light active segment in light mode.
 */
export function SegmentedToggle<T extends string>({
  options,
  value,
  onChange,
  testID,
}: SegmentedToggleProps<T>) {
  const theme = useTheme();
  const c = theme.colors;
  const pill = c.onSurface;
  const activeBg = theme.scheme === 'dark' ? c.background : '#FFFFFF';
  return (
    <View
      testID={testID}
      accessibilityRole="tablist"
      style={[styles.container, theme.shadow.floating, {backgroundColor: pill}]}
    >
      {options.map(option => {
        const active = option.value === value;
        const color = active ? c.onSurface : c.background;
        return (
          <Pressable
            key={option.value}
            testID={`${testID}.${option.value}`}
            accessibilityRole="tab"
            accessibilityState={{selected: active}}
            onPress={() => onChange(option.value)}
            style={[
              styles.segment,
              active ? {backgroundColor: activeBg} : null,
            ]}
          >
            <Icon name={option.icon} size={20} color={color} />
            <Text variant="bodyStrong" style={{color, fontSize: 16}}>
              {option.label}
            </Text>
          </Pressable>
        );
      })}
    </View>
  );
}

const styles = StyleSheet.create({
  container: {
    flexDirection: 'row',
    padding: 4,
    borderRadius: 24,
    alignSelf: 'center',
  },
  segment: {
    height: 40,
    minWidth: 96,
    paddingHorizontal: 18,
    borderRadius: 20,
    flexDirection: 'row',
    alignItems: 'center',
    justifyContent: 'center',
    gap: 8,
  },
});
