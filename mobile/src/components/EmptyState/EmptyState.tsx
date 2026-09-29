import React from 'react';
import {StyleSheet, View} from 'react-native';

import {useTheme} from '@/theme';

import {Button} from '../Button/Button';
import {Text} from '../Text/Text';

export interface EmptyStateAction {
  label: string;
  onPress: () => void;
  testID: string;
}

export interface EmptyStateProps {
  title: string;
  text: string;
  primary?: EmptyStateAction;
  secondary?: EmptyStateAction;
  testID: string;
}

/** Empty/no-result card (screens 01-07, 01-08). */
export function EmptyState({
  title,
  text,
  primary,
  secondary,
  testID,
}: EmptyStateProps) {
  const theme = useTheme();
  return (
    <View
      testID={testID}
      style={[
        styles.card,
        theme.shadow.floating,
        {
          backgroundColor: theme.colors.surface,
          borderColor: theme.colors.outline,
          borderRadius: theme.radius.card,
        },
      ]}
    >
      <Text variant="displayM">{title}</Text>
      <Text variant="body" tone="muted">
        {text}
      </Text>
      {primary || secondary ? (
        <View style={styles.actions}>
          {primary ? <Button {...primary} size="medium" /> : null}
          {secondary ? (
            <Button {...secondary} size="medium" variant="secondary" />
          ) : null}
        </View>
      ) : null}
    </View>
  );
}

const styles = StyleSheet.create({
  card: {padding: 18, gap: 8, borderWidth: 1},
  actions: {flexDirection: 'row', flexWrap: 'wrap', gap: 10, marginTop: 8},
});
