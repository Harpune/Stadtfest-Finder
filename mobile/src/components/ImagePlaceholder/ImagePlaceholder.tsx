import React from 'react';
import {StyleProp, StyleSheet, View, ViewStyle} from 'react-native';
import Svg, {Line} from 'react-native-svg';

import {useTheme} from '@/theme';

import {Text} from '../Text/Text';

// Diagonal stripes (135°, 10 px). Drawn as lines: react-native-svg ignores patternTransform.
const STRIPE_WIDTH = 10;
const STRIPE_EXTENT = 600; // covers the largest placeholder; the view clips the rest
const STRIPES = Array.from(
  {length: Math.ceil((2 * STRIPE_EXTENT) / (STRIPE_WIDTH * 2 * Math.SQRT2))},
  (_, i) => -STRIPE_EXTENT + i * STRIPE_WIDTH * 2 * Math.SQRT2,
);

export interface ImagePlaceholderProps {
  /** Caption bottom left, e.g. "Foto" or "Festfoto". */
  label: string;
  style?: StyleProp<ViewStyle>;
  radius?: number;
}

/** Striped image placeholder (135°, 10 px) until real images arrive in R08. */
export function ImagePlaceholder({
  label,
  style,
  radius = 0,
}: ImagePlaceholderProps) {
  const theme = useTheme();
  const c = theme.colors;
  return (
    <View
      accessibilityElementsHidden
      importantForAccessibility="no-hide-descendants"
      style={[
        styles.box,
        {borderRadius: radius, backgroundColor: c.placeholderB},
        style,
      ]}
    >
      <Svg style={StyleSheet.absoluteFill} width="100%" height="100%">
        {STRIPES.map(offset => (
          <Line
            key={offset}
            x1={offset}
            y1={STRIPE_EXTENT}
            x2={offset + STRIPE_EXTENT}
            y2={0}
            stroke={c.placeholderA}
            strokeWidth={STRIPE_WIDTH}
          />
        ))}
      </Svg>
      <Text
        variant="caption"
        tone="faint"
        style={[styles.label, {fontFamily: 'Menlo'}]}
      >
        {label}
      </Text>
    </View>
  );
}

const styles = StyleSheet.create({
  box: {overflow: 'hidden', justifyContent: 'flex-end'},
  label: {margin: 12, fontSize: 11},
});
