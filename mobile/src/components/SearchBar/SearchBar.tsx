import React, {ReactNode} from 'react';
import {Pressable, StyleSheet, TextInput, View} from 'react-native';

import {strings} from '@/strings/de';
import {useTheme} from '@/theme';

import {Icon} from '../Icon/Icon';

export interface SearchBarProps {
  value: string;
  onChangeText: (text: string) => void;
  testID: string;
  placeholder?: string;
  /** Trailing element, e.g. the filter button. */
  trailing?: ReactNode;
  /** `floating` over the map, `surface` on opaque backgrounds. */
  variant?: 'floating' | 'surface';
}

/** Search field (height 50, radius 16) with amber magnifier and clear button (R03-US5). */
export function SearchBar({
  value,
  onChangeText,
  testID,
  placeholder = strings.discover.searchPlaceholder,
  trailing,
  variant = 'floating',
}: SearchBarProps) {
  const theme = useTheme();
  const c = theme.colors;
  return (
    <View
      style={[
        styles.container,
        variant === 'floating' ? theme.shadow.floating : null,
        {
          backgroundColor: variant === 'floating' ? c.floating : c.surface,
          borderColor: c.outline,
          borderRadius: theme.radius.button,
        },
      ]}
    >
      <Icon name="search" size={20} color={c.primary} />
      <TextInput
        testID={testID}
        value={value}
        onChangeText={onChangeText}
        placeholder={placeholder}
        placeholderTextColor={c.onSurfaceMuted}
        accessibilityLabel={placeholder}
        returnKeyType="search"
        autoCorrect={false}
        autoCapitalize="none"
        maxLength={100}
        style={[
          styles.input,
          {color: c.onSurface, fontFamily: theme.fonts.regular},
        ]}
      />
      {value.length > 0 ? (
        <Pressable
          testID={`${testID}.clear`}
          accessibilityRole="button"
          accessibilityLabel={strings.discover.clearSearch}
          onPress={() => onChangeText('')}
          hitSlop={12}
          style={styles.clear}
        >
          <Icon name="close" size={18} color={c.onSurfaceMuted} />
        </Pressable>
      ) : null}
      {trailing}
    </View>
  );
}

const styles = StyleSheet.create({
  container: {
    flex: 1,
    height: 50,
    borderWidth: 1,
    flexDirection: 'row',
    alignItems: 'center',
    paddingLeft: 16,
    paddingRight: 6,
    gap: 10,
  },
  input: {flex: 1, fontSize: 16, paddingVertical: 0, height: '100%'},
  clear: {padding: 4},
});
