import React from 'react';
import {Pressable, StyleSheet, View} from 'react-native';

import {strings} from '@/strings/de';
import {useTheme} from '@/theme';

export interface ColorPickerProps {
  options: readonly string[];
  value: string;
  onChange: (color: string) => void;
  disabled?: boolean;
  testID: string;
}

/** Round color swatches; the chosen one has a ring (10-02). */
export function ColorPicker({
  options,
  value,
  onChange,
  disabled = false,
  testID,
}: ColorPickerProps) {
  const theme = useTheme();
  return (
    <View style={styles.row} testID={testID} accessibilityRole="radiogroup">
      {options.map((color, index) => {
        const selected = color.toUpperCase() === value.toUpperCase();
        return (
          <Pressable
            key={color}
            accessibilityRole="radio"
            accessibilityLabel={strings.mod.categories.colorLabel(color)}
            accessibilityState={{selected, disabled}}
            disabled={disabled}
            onPress={() => onChange(color)}
            style={[
              styles.ring,
              {borderColor: selected ? theme.colors.onSurface : 'transparent'},
            ]}
            testID={`${testID}.${index}`}
          >
            <View
              style={[
                styles.swatch,
                {
                  backgroundColor: color,
                  opacity: disabled && !selected ? 0.5 : 1,
                },
              ]}
            />
          </Pressable>
        );
      })}
    </View>
  );
}

const styles = StyleSheet.create({
  row: {flexDirection: 'row', flexWrap: 'wrap', gap: 6},
  ring: {padding: 3, borderRadius: 30, borderWidth: 2},
  swatch: {width: 40, height: 40, borderRadius: 20},
});
