import React from 'react';
import {Pressable, StyleSheet, View} from 'react-native';

import {useTheme} from '@/theme';

import {Text} from '../Text/Text';

export interface EmojiPickerProps {
  options: readonly string[];
  value: string;
  onChange: (emoji: string) => void;
  disabled?: boolean;
  testID: string;
}

/** Emoji grid with 6 columns; the chosen one has a turquoise border (10-02). */
export function EmojiPicker({
  options,
  value,
  onChange,
  disabled = false,
  testID,
}: EmojiPickerProps) {
  const theme = useTheme();
  const c = theme.colors;
  return (
    <View style={styles.grid} testID={testID} accessibilityRole="radiogroup">
      {options.map((emoji, index) => {
        const selected = emoji === value;
        return (
          <View key={emoji} style={styles.cell}>
            <Pressable
              accessibilityRole="radio"
              accessibilityLabel={emoji}
              accessibilityState={{selected, disabled}}
              disabled={disabled}
              onPress={() => onChange(emoji)}
              style={({pressed}) => [
                styles.option,
                {
                  backgroundColor: c.surface,
                  borderColor: selected ? c.mod.primary : 'transparent',
                  borderRadius: theme.radius.input,
                  opacity: disabled && !selected ? 0.5 : pressed ? 0.8 : 1,
                },
              ]}
              testID={`${testID}.${index}`}
            >
              <Text style={styles.emoji}>{emoji}</Text>
            </Pressable>
          </View>
        );
      })}
    </View>
  );
}

const styles = StyleSheet.create({
  grid: {flexDirection: 'row', flexWrap: 'wrap', marginHorizontal: -5},
  cell: {width: `${100 / 6}%`, padding: 5},
  option: {
    aspectRatio: 1.1,
    borderWidth: 2,
    alignItems: 'center',
    justifyContent: 'center',
  },
  emoji: {fontSize: 24, lineHeight: 30},
});
