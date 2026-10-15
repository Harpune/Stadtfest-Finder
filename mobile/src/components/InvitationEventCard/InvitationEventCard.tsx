import React from 'react';
import {Pressable, StyleSheet, View} from 'react-native';

import {useTheme} from '@/theme';

import {EventImage} from '../EventImage/EventImage';
import {Icon} from '../Icon/Icon';
import {Text} from '../Text/Text';

export interface InvitationEventCardProps {
  name: string;
  /** Pink line above the name, e.g. "In 8 Tagen". */
  when: string;
  /** "3.–4. Okt · Schwäbisch Gmünd". */
  meta: string;
  imageUrl?: string | null;
  /** Placeholder caption without image. */
  imageLabel: string;
  onPress: () => void;
  testID: string;
}

/** Event card of a received invitation (06-03): photo, countdown, name; opens the detail. */
export function InvitationEventCard({
  name,
  when,
  meta,
  imageUrl,
  imageLabel,
  onPress,
  testID,
}: InvitationEventCardProps) {
  const theme = useTheme();
  const c = theme.colors;
  return (
    <Pressable
      testID={testID}
      onPress={onPress}
      accessibilityRole="button"
      accessibilityLabel={name}
      style={[
        styles.card,
        {backgroundColor: c.surface, borderRadius: theme.radius.card},
      ]}
    >
      <EventImage
        uri={imageUrl}
        label={imageLabel}
        radius={0}
        style={styles.image}
      />
      <View style={styles.body}>
        <View style={styles.text}>
          <Text variant="bodyStrong" tone="secondary">
            {when}
          </Text>
          <Text variant="displayM" numberOfLines={2}>
            {name}
          </Text>
          <Text variant="meta" tone="muted" numberOfLines={1}>
            {meta}
          </Text>
        </View>
        <Icon name="chevronRight" size={18} color={c.onSurfaceMuted} />
      </View>
    </Pressable>
  );
}

const styles = StyleSheet.create({
  card: {overflow: 'hidden'},
  image: {height: 130},
  body: {flexDirection: 'row', alignItems: 'center', padding: 16, gap: 10},
  text: {flex: 1, gap: 2},
});
