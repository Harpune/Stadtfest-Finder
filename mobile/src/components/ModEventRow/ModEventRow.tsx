import React from 'react';
import {Pressable, StyleSheet, View} from 'react-native';

import {strings} from '@/strings/de';
import {useTheme} from '@/theme';

import {Skeleton} from '../Skeleton/Skeleton';
import {Text} from '../Text/Text';

export type ModRowStatus = 'draft' | 'published' | 'past' | 'cancelled';

export interface ModEventRowProps {
  name: string;
  status: ModRowStatus;
  /** Date block, e.g. day "27" and month "SEP"; empty for drafts without date. */
  day: string;
  month: string;
  /** "{Emoji} {Ort} · {Zeitraum}" */
  meta: string;
  favoriteCount: number;
  /** Found by the AI search (R10). */
  autoFound?: boolean;
  onPress: () => void;
  testID: string;
}

/** Row of the moderation overview (08-01). Cancelled: struck through; past: faded. */
export function ModEventRow({
  name,
  status,
  day,
  month,
  meta,
  favoriteCount,
  autoFound = false,
  onPress,
  testID,
}: ModEventRowProps) {
  const theme = useTheme();
  const c = theme.colors;
  const pill = {
    draft: {background: c.surfaceVariant, color: c.onSurfaceMuted},
    published: {background: c.mod.container, color: c.mod.text},
    past: {background: c.surfaceVariant, color: c.onSurfaceMuted},
    cancelled: {background: c.secondaryContainer, color: c.secondaryText},
  }[status];
  return (
    <Pressable
      testID={testID}
      accessibilityRole="button"
      accessibilityLabel={`${name}, ${strings.mod.status[status]}`}
      onPress={onPress}
      style={({pressed}) => [
        styles.row,
        {
          backgroundColor: c.surface,
          borderColor: c.outline,
          borderRadius: theme.radius.card,
          opacity: status === 'past' ? 0.6 : pressed ? 0.85 : 1,
        },
      ]}
    >
      <View style={styles.date}>
        <Text variant="displayM">{day}</Text>
        <Text variant="label" tone="muted" style={styles.month}>
          {month}
        </Text>
      </View>
      <View style={styles.body}>
        <Text
          variant="displayS"
          numberOfLines={2}
          style={[styles.name, status === 'cancelled' ? styles.struck : null]}
        >
          {name}
        </Text>
        <Text variant="meta" tone="muted" numberOfLines={1}>
          {meta}
        </Text>
        <View style={styles.badges}>
          <View style={[styles.pill, {backgroundColor: pill.background}]}>
            <Text
              variant="meta"
              style={{color: pill.color, fontFamily: theme.fonts.semibold}}
            >
              {strings.mod.status[status]}
            </Text>
          </View>
          {autoFound ? (
            <Text variant="meta" tone="mod">
              {strings.mod.autoFound}
            </Text>
          ) : null}
          {favoriteCount > 0 ? (
            <Text variant="meta" tone="muted">
              {strings.mod.favorites(favoriteCount)}
            </Text>
          ) : null}
        </View>
      </View>
      <Text variant="displayS" tone="muted">
        ›
      </Text>
    </Pressable>
  );
}

/** Placeholder row while the overview loads. */
export function ModEventRowSkeleton() {
  const theme = useTheme();
  return (
    <View
      style={[
        styles.row,
        {
          backgroundColor: theme.colors.surface,
          borderColor: theme.colors.outline,
          borderRadius: theme.radius.card,
        },
      ]}
    >
      <View style={styles.date}>
        <Skeleton width={30} height={24} />
      </View>
      <View style={styles.body}>
        <Skeleton width="80%" height={20} />
        <Skeleton width="60%" height={14} />
        <Skeleton width={90} height={24} />
      </View>
    </View>
  );
}

const styles = StyleSheet.create({
  row: {
    flexDirection: 'row',
    alignItems: 'center',
    gap: 12,
    padding: 14,
    borderWidth: 1,
  },
  date: {width: 52, alignItems: 'center'},
  month: {fontSize: 11},
  body: {flex: 1, gap: 4},
  name: {marginBottom: 2},
  struck: {textDecorationLine: 'line-through'},
  badges: {
    flexDirection: 'row',
    alignItems: 'center',
    gap: 10,
    flexWrap: 'wrap',
  },
  pill: {borderRadius: 8, paddingHorizontal: 9, paddingVertical: 3},
});
