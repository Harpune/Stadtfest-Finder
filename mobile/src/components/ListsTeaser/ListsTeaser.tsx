import React from 'react';
import {Pressable, StyleSheet, View} from 'react-native';

import {strings} from '@/strings/de';
import {useTheme} from '@/theme';

import {AvatarStack, StackPerson} from '../AvatarStack/AvatarStack';
import {Text} from '../Text/Text';

export interface ListsTeaserProps {
  /** Up to three people across the lists (overlapping avatars). */
  people: StackPerson[];
  /** "2 Listen · Wiesn-Crew, Familienausflüge"; without lists the invitation text. */
  summary: string;
  onPress: () => void;
  testID: string;
}

/** Compact card "Gemeinsame Listen" above the timeline in the profile drawer (R13-US1). */
export function ListsTeaser({
  people,
  summary,
  onPress,
  testID,
}: ListsTeaserProps) {
  const theme = useTheme();
  const c = theme.colors;
  return (
    <Pressable
      testID={testID}
      accessibilityRole="button"
      accessibilityLabel={`${strings.lists.drawerTitle}, ${summary}`}
      onPress={onPress}
      style={({pressed}) => [
        styles.card,
        {
          backgroundColor: c.surface,
          borderColor: c.outline,
          borderRadius: theme.radius.block,
          opacity: pressed ? 0.85 : 1,
        },
      ]}
    >
      {people.length > 0 ? (
        <AvatarStack people={people} max={3} size={30} />
      ) : null}
      <View style={styles.text}>
        <Text variant="bodyStrong" numberOfLines={1}>
          {strings.lists.drawerTitle}
        </Text>
        <Text variant="meta" tone="muted" numberOfLines={1}>
          {summary}
        </Text>
      </View>
      <Text variant="bodyStrong" tone="muted">
        ›
      </Text>
    </Pressable>
  );
}

const styles = StyleSheet.create({
  card: {
    flexDirection: 'row',
    alignItems: 'center',
    gap: 12,
    padding: 12,
    borderWidth: 1,
  },
  text: {flex: 1, gap: 2},
});
