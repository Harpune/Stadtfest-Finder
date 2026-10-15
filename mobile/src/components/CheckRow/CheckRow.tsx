import React, {ReactNode} from 'react';
import {Pressable, StyleSheet, View} from 'react-native';

import {useTheme} from '@/theme';

import {Icon} from '../Icon/Icon';
import {Text} from '../Text/Text';

export interface CheckRowProps {
  label: string;
  /** Second line, e.g. date and place of an event. */
  meta?: string;
  /** Leading element, e.g. an avatar or emoji tile. */
  lead?: ReactNode;
  checked: boolean;
  onPress: () => void;
  disabled?: boolean;
  testID: string;
}

/** Row with a round check (multiple choice in sheets, 05-02). */
export function CheckRow({
  label,
  meta,
  lead,
  checked,
  onPress,
  disabled = false,
  testID,
}: CheckRowProps) {
  const theme = useTheme();
  const c = theme.colors;
  return (
    <Pressable
      testID={testID}
      accessibilityRole="checkbox"
      accessibilityState={{checked, disabled}}
      accessibilityLabel={meta ? `${label}, ${meta}` : label}
      onPress={onPress}
      disabled={disabled}
      style={({pressed}) => [
        styles.row,
        {
          borderBottomColor: c.outline,
          opacity: disabled ? 0.5 : pressed ? 0.8 : 1,
        },
      ]}
    >
      {lead}
      <View style={styles.text}>
        <Text variant="body" numberOfLines={1}>
          {label}
        </Text>
        {meta ? (
          <Text variant="meta" tone="muted" numberOfLines={1}>
            {meta}
          </Text>
        ) : null}
      </View>
      <View
        style={[
          styles.check,
          checked
            ? {backgroundColor: c.primary, borderColor: c.primary}
            : {borderColor: c.outline},
        ]}
      >
        {checked ? (
          <Icon name="check" size={16} color={c.onPrimary} strokeWidth={3} />
        ) : null}
      </View>
    </Pressable>
  );
}

const styles = StyleSheet.create({
  row: {
    flexDirection: 'row',
    alignItems: 'center',
    gap: 14,
    paddingVertical: 12,
    borderBottomWidth: StyleSheet.hairlineWidth,
  },
  text: {flex: 1, gap: 2},
  check: {
    width: 28,
    height: 28,
    borderRadius: 14,
    borderWidth: 2,
    alignItems: 'center',
    justifyContent: 'center',
  },
});
