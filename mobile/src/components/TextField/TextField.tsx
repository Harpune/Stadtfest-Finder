import React from 'react';
import {StyleSheet, TextInput, TextInputProps, View} from 'react-native';

import {useTheme} from '@/theme';

import {Text} from '../Text/Text';

export interface TextFieldProps extends Pick<
  TextInputProps,
  'autoComplete' | 'textContentType' | 'autoFocus' | 'onSubmitEditing'
> {
  label: string;
  value: string;
  onChangeText: (text: string) => void;
  testID: string;
  /** Error text below the field; also colors the border. */
  error?: string;
  disabled?: boolean;
  maxLength?: number;
}

/** Labeled text input (height 52, radius 14) as in the login design (03-04). */
export function TextField({
  label,
  value,
  onChangeText,
  testID,
  error,
  disabled = false,
  maxLength,
  ...inputProps
}: TextFieldProps) {
  const theme = useTheme();
  const c = theme.colors;
  return (
    <View style={styles.container}>
      <Text variant="label">{label}</Text>
      <TextInput
        {...inputProps}
        testID={testID}
        value={value}
        onChangeText={onChangeText}
        editable={!disabled}
        maxLength={maxLength}
        accessibilityLabel={label}
        accessibilityState={{disabled}}
        placeholderTextColor={c.onSurfaceMuted}
        style={[
          styles.input,
          {
            color: c.onSurface,
            backgroundColor: c.surface,
            borderColor: error ? c.error : c.outline,
            borderRadius: theme.radius.input,
            fontFamily: theme.fonts.regular,
            opacity: disabled ? 0.5 : 1,
          },
        ]}
      />
      {error ? (
        <Text variant="caption" tone="error" testID={`${testID}.error`}>
          {error}
        </Text>
      ) : null}
    </View>
  );
}

const styles = StyleSheet.create({
  container: {gap: 6},
  input: {height: 52, borderWidth: 1, paddingHorizontal: 16, fontSize: 16},
});
