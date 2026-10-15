import React from 'react';
import {Pressable, StyleSheet, View} from 'react-native';

import {strings} from '@/strings/de';
import {useTheme} from '@/theme';

import {AvatarStack, StackPerson} from '../AvatarStack/AvatarStack';
import {Text} from '../Text/Text';

export interface SharedListCardProps {
  name: string;
  eventCount: number;
  people: StackPerson[];
  /** "🎄 Ulmer Weihnachtsmarkt · 23. Nov – 22. Dez"; hidden without an upcoming event. */
  next?: string;
  onPress: () => void;
  testID: string;
}

/** Card of the list overview (05-01): name, count, avatars, persons and the next event. */
export function SharedListCard({
  name,
  eventCount,
  people,
  next,
  onPress,
  testID,
}: SharedListCardProps) {
  const theme = useTheme();
  const c = theme.colors;
  const s = strings.lists;
  return (
    <Pressable
      testID={testID}
      accessibilityRole="button"
      accessibilityLabel={`${name}, ${s.events(eventCount)}, ${s.people(people.length)}`}
      onPress={onPress}
      style={({pressed}) => [
        styles.card,
        {
          backgroundColor: c.surface,
          borderColor: c.outline,
          borderRadius: theme.radius.card,
          opacity: pressed ? 0.85 : 1,
        },
      ]}
    >
      <View style={styles.header}>
        <Text variant="displayM" style={styles.name}>
          {name}
        </Text>
        <Text variant="meta" tone="muted">
          {s.events(eventCount)}
        </Text>
      </View>
      <View style={styles.people}>
        <AvatarStack people={people} size={34} />
        <Text variant="body" tone="muted">
          {s.people(people.length)}
        </Text>
      </View>
      {next ? (
        <View
          style={[
            styles.next,
            {
              backgroundColor: c.surfaceVariant,
              borderRadius: theme.radius.input,
            },
          ]}
        >
          <Text variant="meta">
            {s.next} {next}
          </Text>
        </View>
      ) : null}
    </Pressable>
  );
}

const styles = StyleSheet.create({
  card: {padding: 16, gap: 12, borderWidth: 1},
  header: {flexDirection: 'row', alignItems: 'flex-start', gap: 12},
  name: {flex: 1},
  people: {flexDirection: 'row', alignItems: 'center', gap: 10},
  next: {paddingHorizontal: 12, paddingVertical: 10},
});
