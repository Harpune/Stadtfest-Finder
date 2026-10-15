import React from 'react';
import {Pressable, StyleSheet} from 'react-native';

import {useTheme} from '@/theme';

import {AvatarStack, StackPerson} from '../AvatarStack/AvatarStack';
import {Icon} from '../Icon/Icon';
import {Text} from '../Text/Text';

export interface ComingAlongHintProps {
  people: StackPerson[];
  /** "Jonas und Tim kommen mit". */
  text: string;
  onPress: () => void;
  testID: string;
}

/** Hint on the detail page (02-04): avatars of who comes along; opens the invitation. */
export function ComingAlongHint({
  people,
  text,
  onPress,
  testID,
}: ComingAlongHintProps) {
  const theme = useTheme();
  return (
    <Pressable
      testID={testID}
      onPress={onPress}
      accessibilityRole="button"
      accessibilityLabel={text}
      style={[
        styles.hint,
        {
          backgroundColor: theme.colors.surface,
          borderRadius: theme.radius.block,
        },
      ]}
    >
      <AvatarStack people={people} max={3} size={32} />
      <Text variant="body" style={styles.text} numberOfLines={2}>
        {text}
      </Text>
      <Icon name="chevronRight" size={18} color={theme.colors.onSurfaceMuted} />
    </Pressable>
  );
}

const styles = StyleSheet.create({
  hint: {
    flexDirection: 'row',
    alignItems: 'center',
    gap: 12,
    paddingHorizontal: 14,
    paddingVertical: 12,
  },
  text: {flex: 1},
});
