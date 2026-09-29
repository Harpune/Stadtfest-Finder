import Slider from '@react-native-community/slider';
import React from 'react';
import {StyleSheet, View} from 'react-native';

import {useTheme} from '@/theme';

import {Text} from '../Text/Text';

export interface RangeSliderProps {
  /** Section label, e.g. "Radius". */
  label: string;
  /** Value text on the right, e.g. "bis 25 km". */
  formatValue: (value: number) => string;
  /** Unit for the min/max labels, e.g. "km". */
  unit: string;
  value: number;
  onChange: (value: number) => void;
  min: number;
  max: number;
  step: number;
  /** Caption between the min and max labels, e.g. "vom Standort Aalen". */
  caption: string;
  testID: string;
  disabled?: boolean;
}

/** Range slider with label, value text and min/max labels (e.g. notification radius, R11). */
export function RangeSlider({
  label,
  formatValue,
  unit,
  value,
  onChange,
  min,
  max,
  step,
  caption,
  testID,
  disabled = false,
}: RangeSliderProps) {
  const theme = useTheme();
  const c = theme.colors;
  return (
    <View style={styles.container}>
      <View style={styles.header}>
        <Text variant="label">{label}</Text>
        <Text variant="bodyStrong" testID={`${testID}.value`}>
          {formatValue(value)}
        </Text>
      </View>
      <Slider
        testID={testID}
        accessibilityLabel={label}
        value={value}
        minimumValue={min}
        maximumValue={max}
        step={step}
        disabled={disabled}
        onValueChange={v => onChange(Math.round(v))}
        minimumTrackTintColor={c.primary}
        maximumTrackTintColor={c.surfaceVariant}
        thumbTintColor={c.primary}
        style={styles.slider}
      />
      <View style={styles.labels}>
        <Text variant="meta" tone="muted">
          {`${min} ${unit}`}
        </Text>
        <Text
          variant="meta"
          tone="muted"
          numberOfLines={1}
          style={styles.caption}
        >
          {caption}
        </Text>
        <Text variant="meta" tone="muted">
          {`${max} ${unit}`}
        </Text>
      </View>
    </View>
  );
}

const styles = StyleSheet.create({
  container: {gap: 6},
  header: {
    flexDirection: 'row',
    justifyContent: 'space-between',
    alignItems: 'center',
  },
  slider: {height: 40},
  labels: {flexDirection: 'row', justifyContent: 'space-between', gap: 8},
  caption: {flexShrink: 1, textAlign: 'center'},
});
