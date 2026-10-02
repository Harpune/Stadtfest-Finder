import React from 'react';
import {Pressable, StyleSheet, View} from 'react-native';

import type {EventStatusTone} from '@/features/events/status';
import {strings} from '@/strings/de';
import {useTheme} from '@/theme';

import {FavoriteButton} from '../FavoriteButton/FavoriteButton';
import {EventImage} from '../EventImage/EventImage';
import {Skeleton} from '../Skeleton/Skeleton';
import {Text} from '../Text/Text';
import {StatusText} from '../StatusText/StatusText';

export interface EventListCardProps {
  name: string;
  statusLabel: string;
  statusTone: EventStatusTone;
  dateRange: string;
  city: string;
  categoryName: string;
  emoji: string;
  distanceLabel?: string;
  /** Card variant of the cover image (R08); the striped placeholder without it. */
  imageUrl?: string | null;
  onPress: () => void;
  onFavoritePress: () => void;
  /** Filled heart for favorites of the signed-in user (R06-US1). */
  isFavorite?: boolean;
  testID: string;
}

/** List card: image 160, running badge, heart, status, serif name, pills (R03-US4). */
export function EventListCard({
  name,
  statusLabel,
  statusTone,
  dateRange,
  city,
  categoryName,
  emoji,
  distanceLabel,
  imageUrl,
  onPress,
  onFavoritePress,
  isFavorite = false,
  testID,
}: EventListCardProps) {
  const theme = useTheme();
  const c = theme.colors;
  return (
    <Pressable
      testID={testID}
      accessibilityRole="button"
      accessibilityLabel={`${name}, ${statusLabel}, ${dateRange}, ${city}`}
      onPress={onPress}
      style={({pressed}) => [
        styles.card,
        {
          backgroundColor: c.surface,
          borderColor: c.outline,
          borderRadius: theme.radius.card,
          opacity: pressed ? 0.9 : 1,
        },
      ]}
    >
      <View>
        <EventImage
          uri={imageUrl}
          label={strings.discover.eventPhoto}
          style={styles.image}
          testID={`${testID}.image`}
        />
        {statusTone === 'running' ? (
          <View style={[styles.badge, {backgroundColor: c.primary}]}>
            <View style={[styles.badgeDot, {backgroundColor: c.onPrimary}]} />
            <Text
              variant="meta"
              style={{color: c.onPrimary, fontFamily: theme.fonts.semibold}}
            >
              {strings.discover.runningNow}
            </Text>
          </View>
        ) : null}
        <View style={styles.heart}>
          <FavoriteButton
            active={isFavorite}
            accessibilityLabel={
              isFavorite
                ? strings.favorites.remove(name)
                : strings.favorites.add(name)
            }
            onPress={onFavoritePress}
            testID={`${testID}.favorite`}
            size={40}
            iconSize={20}
          />
        </View>
      </View>
      <View style={styles.body}>
        <StatusText label={statusLabel} tone={statusTone} />
        <Text variant="displayM" style={styles.name}>
          {name}
        </Text>
        <Text variant="body" tone="muted" numberOfLines={1}>
          {dateRange} · {city}
        </Text>
        <View style={styles.pills}>
          <Pill label={`${emoji} ${categoryName}`} />
          {distanceLabel ? <Pill label={distanceLabel} /> : null}
        </View>
      </View>
    </Pressable>
  );
}

function Pill({label}: {label: string}) {
  const theme = useTheme();
  return (
    <View
      style={[
        styles.pill,
        {
          backgroundColor: theme.colors.surfaceVariant,
          borderRadius: theme.radius.pill,
        },
      ]}
    >
      <Text variant="meta">{label}</Text>
    </View>
  );
}

/** Loading placeholder of a list card (screen 01-04). */
export function EventListCardSkeleton() {
  const theme = useTheme();
  return (
    <View
      style={[
        styles.card,
        {
          backgroundColor: theme.colors.surface,
          borderColor: theme.colors.outline,
          borderRadius: theme.radius.card,
        },
      ]}
    >
      <Skeleton height={160} radius={0} />
      <View style={[styles.body, {gap: 10}]}>
        <Skeleton width={120} height={12} />
        <Skeleton width={220} height={20} />
        <Skeleton width={160} height={12} />
      </View>
    </View>
  );
}

const styles = StyleSheet.create({
  card: {borderWidth: 1, overflow: 'hidden'},
  image: {height: 160},
  badge: {
    position: 'absolute',
    top: 12,
    left: 12,
    flexDirection: 'row',
    alignItems: 'center',
    gap: 6,
    paddingHorizontal: 12,
    height: 28,
    borderRadius: 14,
  },
  badgeDot: {width: 9, height: 9, borderRadius: 5},
  heart: {position: 'absolute', top: 10, right: 10},
  body: {padding: 14, gap: 4},
  name: {fontSize: 20, lineHeight: 25},
  pills: {flexDirection: 'row', gap: 8, marginTop: 8},
  pill: {paddingHorizontal: 10, paddingVertical: 6},
});
