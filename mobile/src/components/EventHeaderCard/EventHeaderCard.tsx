import React from 'react';
import {Pressable, StyleSheet, View} from 'react-native';

import {useTheme} from '@/theme';

import {EventImage} from '../EventImage/EventImage';
import {Text} from '../Text/Text';

export interface EventHeaderCardProps {
  name: string;
  /** "19. Sep – 4. Okt · München". */
  meta: string;
  imageUrl?: string | null;
  /** Opens the event detail; without it the card is not tappable. */
  onPress?: () => void;
  testID?: string;
}

/** Compact event head of the invitation screens (06-01, 06-02): image 56, name, meta. */
export function EventHeaderCard({
  name,
  meta,
  imageUrl,
  onPress,
  testID,
}: EventHeaderCardProps) {
  const theme = useTheme();
  return (
    <Pressable
      testID={testID}
      onPress={onPress}
      disabled={!onPress}
      accessibilityRole={onPress ? 'button' : undefined}
      style={[
        styles.card,
        {
          backgroundColor: theme.colors.surface,
          borderRadius: theme.radius.block,
        },
      ]}
    >
      <EventImage uri={imageUrl} label="" radius={14} style={styles.image} />
      <View style={styles.text}>
        <Text variant="displayS" numberOfLines={2}>
          {name}
        </Text>
        <Text variant="meta" tone="muted" numberOfLines={1}>
          {meta}
        </Text>
      </View>
    </Pressable>
  );
}

const styles = StyleSheet.create({
  card: {flexDirection: 'row', alignItems: 'center', gap: 14, padding: 10},
  image: {width: 56, height: 56},
  text: {flex: 1, gap: 2},
});
