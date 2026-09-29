import React from 'react';
import {StyleProp, StyleSheet, View, ViewStyle} from 'react-native';
import Svg, {Defs, Line, Pattern, Rect} from 'react-native-svg';

import {useTheme} from '@/theme';

import {Text} from '../Text/Text';

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
        <Defs>
          <Pattern
            id="stripes"
            patternUnits="userSpaceOnUse"
            width={20}
            height={20}
            patternTransform="rotate(45)"
          >
            <Rect width={20} height={20} fill={c.placeholderB} />
            <Line
              x1={0}
              y1={0}
              x2={0}
              y2={20}
              stroke={c.placeholderA}
              strokeWidth={20}
            />
          </Pattern>
        </Defs>
        <Rect width="100%" height="100%" fill="url(#stripes)" />
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
