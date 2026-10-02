import React from 'react';
import {StyleSheet, TextInput, TextInputProps, View} from 'react-native';

import {useTheme} from '@/theme';

import {Text} from '../Text/Text';

export interface TextFieldProps extends Pick<
  TextInputProps,
  | 'autoComplete'
  | 'textContentType'
  | 'autoFocus'
  | 'onSubmitEditing'
  | 'placeholder'
  | 'keyboardType'
  | 'autoCapitalize'
  | 'onFocus'
> {
  label: string;
  value: string;
  onChangeText: (text: string) => void;
  testID: string;
  /** Error text below the field; also colors the border. */
  error?: string;
  disabled?: boolean;
  maxLength?: number;
  /** Multi-line text area (min. height 110), e.g. description. */
  multiline?: boolean;
  /** Hide the label (e.g. second field under one heading). */
  hideLabel?: boolean;
  /** `code`: large spaced digits, e.g. a postal code (09-01). */
  variant?: 'default' | 'code';
  /** Border color of a valid, focused-looking field (e.g. the moderation accent). */
  accentColor?: string;
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
  multiline = false,
  hideLabel = false,
  variant = 'default',
  accentColor,
  ...inputProps
}: TextFieldProps) {
  const theme = useTheme();
  const c = theme.colors;
  return (
    <View style={styles.container}>
      {hideLabel ? null : <Text variant="label">{label}</Text>}
      <TextInput
        {...inputProps}
        testID={testID}
        value={value}
        onChangeText={onChangeText}
        editable={!disabled}
        maxLength={maxLength}
        multiline={multiline}
        textAlignVertical={multiline ? 'top' : 'center'}
        accessibilityLabel={label}
        accessibilityState={{disabled}}
        placeholderTextColor={c.onSurfaceMuted}
        style={[
          styles.input,
          multiline ? styles.multiline : null,
          variant === 'code'
            ? [styles.code, {fontFamily: theme.fonts.semibold}]
            : null,
          {
            color: c.onSurface,
            backgroundColor: c.surface,
            borderColor: error ? c.error : (accentColor ?? c.outline),
            borderRadius: theme.radius.input,
            ...(variant === 'code' ? null : {fontFamily: theme.fonts.regular}),
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
  // 22/600 with 0.12 em tracking (09-01).
  code: {height: 64, fontSize: 22, letterSpacing: 2.64},
  multiline: {
    height: undefined,
    minHeight: 110,
    paddingTop: 14,
    paddingBottom: 14,
  },
});
