import React from 'react';
import {Pressable, StyleSheet, Switch, View} from 'react-native';

import {useTheme} from '@/theme';

import {Text} from '../Text/Text';

export interface MenuRowProps {
  label: string;
  /** `primary` (amber) for the moderator link, `secondary` (pink) for "Abmelden". */
  tone?: 'default' | 'primary' | 'secondary';
  onPress?: () => void;
  onLongPress?: () => void;
  /** Shows a switch instead of the chevron (e.g. "Dunkelmodus"). */
  switchValue?: boolean;
  onSwitchChange?: (value: boolean) => void;
  /** Chevron "›" for rows that open another screen. */
  chevron?: boolean;
  accessibilityHint?: string;
  testID: string;
}

/** Row of the drawer footer: label with switch, chevron or plain action. */
export function MenuRow({
  label,
  tone = 'default',
  onPress,
  onLongPress,
  switchValue,
  onSwitchChange,
  chevron = false,
  accessibilityHint,
  testID,
}: MenuRowProps) {
  const theme = useTheme();
  const c = theme.colors;
  const hasSwitch = switchValue !== undefined;
  const color =
    tone === 'primary'
      ? c.primary
      : tone === 'secondary'
        ? c.secondary
        : c.onSurface;
  return (
    <Pressable
      testID={testID}
      accessibilityRole={hasSwitch ? 'switch' : 'button'}
      accessibilityState={hasSwitch ? {checked: switchValue} : undefined}
      accessibilityHint={accessibilityHint}
      onPress={hasSwitch ? () => onSwitchChange?.(!switchValue) : onPress}
      onLongPress={onLongPress}
      style={({pressed}) => [styles.row, {opacity: pressed ? 0.7 : 1}]}
    >
      <Text
        variant="bodyStrong"
        style={[styles.label, {color, fontSize: 16}]}
        numberOfLines={1}
      >
        {label}
      </Text>
      {hasSwitch ? (
        <Switch
          value={switchValue}
          onValueChange={onSwitchChange}
          trackColor={{false: c.surfaceVariant, true: c.primary}}
          // Light thumb in both schemes (Android would tint it with the system accent).
          thumbColor={theme.scheme === 'dark' ? c.onSurface : c.surface}
          ios_backgroundColor={c.surfaceVariant}
          testID={`${testID}.switch`}
          accessibilityElementsHidden
          importantForAccessibility="no"
        />
      ) : chevron ? (
        <View>
          <Text variant="bodyStrong" style={{color}}>
            ›
          </Text>
        </View>
      ) : null}
    </Pressable>
  );
}

const styles = StyleSheet.create({
  row: {
    minHeight: 44,
    flexDirection: 'row',
    alignItems: 'center',
    gap: 12,
  },
  label: {flex: 1},
});
