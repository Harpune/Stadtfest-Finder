import React from 'react';
import {StyleSheet, Switch, View} from 'react-native';

import {useTheme} from '@/theme';

import {Text} from '../Text/Text';

export interface SwitchRowProps {
  label: string;
  hint?: string;
  value: boolean;
  onChange: (value: boolean) => void;
  disabled?: boolean;
  /** `mod`: turquoise track (moderation view). */
  accent?: 'primary' | 'mod';
  testID: string;
}

/** Label with an optional hint and a switch on the right. */
export function SwitchRow({
  label,
  hint,
  value,
  onChange,
  disabled = false,
  accent = 'primary',
  testID,
}: SwitchRowProps) {
  const theme = useTheme();
  const c = theme.colors;
  const on = accent === 'mod' ? c.mod.primary : c.primary;
  return (
    <View style={styles.row}>
      <View style={styles.text}>
        <Text variant="bodyStrong">{label}</Text>
        {hint ? (
          <Text variant="caption" tone="muted">
            {hint}
          </Text>
        ) : null}
      </View>
      <Switch
        accessibilityLabel={label}
        value={value}
        onValueChange={onChange}
        disabled={disabled}
        trackColor={{false: c.outline, true: on}}
        thumbColor="#FFFFFF"
        ios_backgroundColor={c.outline}
        testID={testID}
      />
    </View>
  );
}

const styles = StyleSheet.create({
  row: {flexDirection: 'row', alignItems: 'center', gap: 12},
  text: {flex: 1, gap: 2},
});
