import React from 'react';
import {Pressable, StyleSheet, View} from 'react-native';

import type {EventStatusTone} from '@/features/events/status';
import {strings} from '@/strings/de';
import {useTheme} from '@/theme';

import {ImagePlaceholder} from '../ImagePlaceholder/ImagePlaceholder';
import {Skeleton} from '../Skeleton/Skeleton';
import {Text} from '../Text/Text';
import {StatusText} from './StatusText';

export const CAROUSEL_CARD_WIDTH = 300;
export const CAROUSEL_CARD_HEIGHT = 106;

export interface EventCarouselCardProps {
  name: string;
  statusLabel: string;
  statusTone: EventStatusTone;
  dateRange: string;
  city: string;
  emoji: string;
  distanceLabel?: string;
  selected?: boolean;
  onPress: () => void;
  testID: string;
}

/** Carousel card (300 × ≈ 106): image 84, status, name, date range, place (R03-US3). */
export function EventCarouselCard({
  name,
  statusLabel,
  statusTone,
  dateRange,
  city,
  emoji,
  distanceLabel,
  selected = false,
  onPress,
  testID,
}: EventCarouselCardProps) {
  const theme = useTheme();
  const c = theme.colors;
  const place = distanceLabel ? `${city} · ${distanceLabel}` : city;
  return (
    <Pressable
      testID={testID}
      accessibilityRole="button"
      accessibilityState={{selected}}
      accessibilityLabel={`${name}, ${statusLabel}, ${dateRange}, ${place}`}
      onPress={onPress}
      style={[
        styles.card,
        theme.shadow.floating,
        {
          backgroundColor: c.surface,
          borderRadius: theme.radius.card,
          borderColor: selected ? 'rgba(255,181,71,0.7)' : c.outline,
        },
      ]}
    >
      <ImagePlaceholder
        label={strings.discover.photo}
        style={styles.image}
        radius={14}
      />
      <View style={styles.body}>
        <StatusText label={statusLabel} tone={statusTone} />
        <Text variant="displayS" numberOfLines={1} style={styles.name}>
          {name}
        </Text>
        <Text variant="meta" tone="muted" numberOfLines={1}>
          {dateRange}
        </Text>
        <Text variant="meta" tone="muted" numberOfLines={1}>
          {emoji} {place}
        </Text>
      </View>
    </Pressable>
  );
}

/** Loading placeholder with the size of a carousel card (screen 01-02). */
export function EventCarouselCardSkeleton() {
  const theme = useTheme();
  return (
    <View
      style={[
        styles.card,
        {
          backgroundColor: theme.colors.surface,
          borderRadius: theme.radius.card,
          borderColor: theme.colors.outline,
        },
      ]}
    >
      <Skeleton width={84} height={84} radius={14} />
      <View style={[styles.body, styles.skeletonBody]}>
        <Skeleton width={110} height={12} />
        <Skeleton width={170} height={18} />
        <Skeleton width={130} height={12} />
      </View>
    </View>
  );
}

const styles = StyleSheet.create({
  card: {
    width: CAROUSEL_CARD_WIDTH,
    height: CAROUSEL_CARD_HEIGHT,
    borderWidth: 1.5,
    flexDirection: 'row',
    alignItems: 'center',
    padding: 10,
    gap: 12,
  },
  image: {width: 84, height: 84},
  body: {flex: 1, gap: 2},
  skeletonBody: {gap: 8},
  name: {fontSize: 18, lineHeight: 23},
});
