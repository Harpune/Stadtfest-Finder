import React from 'react';
import {StyleSheet, View} from 'react-native';

import {useTheme} from '@/theme';

import {Avatar} from '../Avatar/Avatar';

export interface StackPerson {
  id: string;
  initials: string;
  /** Avatar color; without it the neutral user color is used (own account). */
  color?: string;
}

export interface AvatarStackProps {
  people: StackPerson[];
  /** Maximum number of avatars shown. */
  max?: number;
  size?: number;
  testID?: string;
}

/** Overlapping avatars, e.g. members of a shared list (05-01, drawer card). */
export function AvatarStack({
  people,
  max = 4,
  size = 36,
  testID,
}: AvatarStackProps) {
  const theme = useTheme();
  return (
    <View style={styles.row} testID={testID} accessibilityElementsHidden>
      {people.slice(0, max).map((person, index) => (
        <View
          key={person.id}
          style={[
            styles.item,
            {
              marginLeft: index === 0 ? 0 : -size * 0.28,
              borderRadius: size / 2 + 2,
              borderColor: theme.colors.surface,
            },
          ]}
        >
          <Avatar initials={person.initials} color={person.color} size={size} />
        </View>
      ))}
    </View>
  );
}

const styles = StyleSheet.create({
  row: {flexDirection: 'row', alignItems: 'center'},
  item: {borderWidth: 2},
});
