import React from 'react';
import {Pressable, StyleSheet, View} from 'react-native';

import {strings} from '@/strings/de';
import {useTheme} from '@/theme';

import {Text} from '../Text/Text';

export interface MonthGridOption {
  value: string;
  label: string;
}

export interface MonthGridProps {
  options: readonly MonthGridOption[];
  selected: readonly string[];
  onToggle: (value: string) => void;
  testID: string;
}

/** Month grid with 4 columns and multi-select (E-03, screen 01-06). */
export function MonthGrid({
  options,
  selected,
  onToggle,
  testID,
}: MonthGridProps) {
  const theme = useTheme();
  const c = theme.colors;
  return (
    <View
      testID={testID}
      style={[
        styles.box,
        {backgroundColor: c.surfaceVariant, borderRadius: theme.radius.block},
      ]}
    >
      <Text variant="meta" tone="muted">
        {strings.filter.monthsHint}
      </Text>
      <View style={styles.grid}>
        {options.map(option => {
          const active = selected.includes(option.value);
          return (
            <Pressable
              key={option.value}
              testID={`${testID}.${option.value}`}
              accessibilityRole="button"
              accessibilityState={{selected: active}}
              onPress={() => onToggle(option.value)}
              style={({pressed}) => [
                styles.cell,
                {
                  backgroundColor: active ? c.primary : c.sheet,
                  borderRadius: theme.radius.chip,
                  opacity: pressed ? 0.8 : 1,
                },
              ]}
            >
              <Text
                variant="bodyStrong"
                style={{color: active ? c.onPrimary : c.onSurface}}
              >
                {option.label}
              </Text>
            </Pressable>
          );
        })}
      </View>
    </View>
  );
}

const styles = StyleSheet.create({
  box: {padding: 12, gap: 10},
  grid: {flexDirection: 'row', flexWrap: 'wrap', gap: 8},
  cell: {
    width: '22.5%',
    flexGrow: 1,
    height: 44,
    alignItems: 'center',
    justifyContent: 'center',
  },
});
