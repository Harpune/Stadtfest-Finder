import Slider from '@react-native-community/slider';
import React from 'react';
import {StyleSheet, View} from 'react-native';

import {strings} from '@/strings/de';
import {useTheme} from '@/theme';

import {Text} from '../Text/Text';

export interface RangeSliderProps {
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

/** Distance slider with "bis {n} km" and min/max labels (R03-US7). */
export function RangeSlider({
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
        <Text variant="label">{strings.filter.distance}</Text>
        <Text variant="bodyStrong" testID={`${testID}.value`}>
          {strings.filter.upTo(value)}
        </Text>
      </View>
      <Slider
        testID={testID}
        accessibilityLabel={strings.filter.distance}
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
          {strings.filter.km(min)}
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
          {strings.filter.km(max)}
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
