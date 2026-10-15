import React from 'react';
import {Pressable, StyleSheet, View} from 'react-native';

import {strings} from '@/strings/de';
import {useTheme} from '@/theme';

import {Avatar} from '../Avatar/Avatar';
import {Icon} from '../Icon/Icon';
import {Text} from '../Text/Text';

export interface MemberAvatarProps {
  initials: string;
  color?: string;
  /** First name or "Du". */
  label: string;
  /** Edit mode (05-04): pink ✕ at the avatar; never for the own account. */
  onRemove?: () => void;
  testID: string;
}

/** Member of a shared list: avatar 48 with the first name below (05-03). */
export function MemberAvatar({
  initials,
  color,
  label,
  onRemove,
  testID,
}: MemberAvatarProps) {
  const theme = useTheme();
  const c = theme.colors;
  return (
    <View style={styles.item} testID={testID}>
      <View>
        <Avatar initials={initials} color={color} size={48} />
        {onRemove ? (
          <Pressable
            testID={`${testID}.remove`}
            accessibilityRole="button"
            accessibilityLabel={strings.lists.removeMember(label)}
            onPress={onRemove}
            hitSlop={10}
            style={[styles.remove, {backgroundColor: c.secondary}]}
          >
            <Icon
              name="close"
              size={12}
              color={c.onSecondary}
              strokeWidth={3}
            />
          </Pressable>
        ) : null}
      </View>
      <Text variant="meta" tone="muted" numberOfLines={1}>
        {label}
      </Text>
    </View>
  );
}

const styles = StyleSheet.create({
  item: {alignItems: 'center', gap: 6, width: 64},
  remove: {
    position: 'absolute',
    top: -4,
    right: -6,
    width: 22,
    height: 22,
    borderRadius: 11,
    alignItems: 'center',
    justifyContent: 'center',
  },
});
