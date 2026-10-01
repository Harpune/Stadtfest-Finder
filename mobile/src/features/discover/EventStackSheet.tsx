/**
 * Festivals at (almost) the same spot, e.g. two events on one market square. Zooming cannot
 * split their cluster, so a tap on it lists them here; a tap on an entry opens the detail.
 */
import React from 'react';
import {Pressable, StyleSheet, View} from 'react-native';

import {BottomSheet, StatusText, Text} from '@/components';
import {formatDateRange, IsoDate} from '@/features/events/dates';
import {eventStatus} from '@/features/events/status';
import {strings} from '@/strings/de';
import {useTheme} from '@/theme';

import type {CategoryLook} from './categoryLookup';
import type {EventSummary} from './useDiscoverData';

export interface EventStackSheetProps {
  /** Events of the tapped cluster; null hides the sheet. */
  events: EventSummary[] | null;
  today: IsoDate;
  categoryOf: (id: string) => CategoryLook;
  onOpen: (event: EventSummary) => void;
  onClose: () => void;
}

export function EventStackSheet({
  events,
  today,
  categoryOf,
  onOpen,
  onClose,
}: EventStackSheetProps) {
  const theme = useTheme();
  const c = theme.colors;
  const sorted = [...(events ?? [])].sort(
    (a, b) =>
      a.startDate.localeCompare(b.startDate) || a.name.localeCompare(b.name),
  );
  return (
    <BottomSheet
      visible={events !== null}
      onClose={onClose}
      title={strings.discover.stackTitle(sorted.length)}
      testID="discover.stack"
    >
      <View style={styles.list}>
        {sorted.map(event => {
          const category = categoryOf(event.categoryId);
          const status = eventStatus(event, today);
          return (
            <Pressable
              key={event.id}
              testID={`discover.stack.item.${event.id}`}
              accessibilityRole="button"
              accessibilityLabel={`${event.name}, ${status.label}, ${formatDateRange(
                event.startDate,
                event.endDate,
              )}`}
              onPress={() => onOpen(event)}
              style={({pressed}) => [
                styles.row,
                {
                  backgroundColor: c.surface,
                  borderColor: c.outline,
                  borderRadius: theme.radius.card,
                  opacity: pressed ? 0.85 : 1,
                },
              ]}
            >
              <View
                style={[
                  styles.bubble,
                  {
                    backgroundColor: c.surfaceVariant,
                    borderColor: category.color,
                  },
                ]}
              >
                <Text style={styles.emoji}>{category.emoji}</Text>
              </View>
              <View style={styles.text}>
                <StatusText label={status.label} tone={status.tone} />
                <Text variant="displayS" numberOfLines={2}>
                  {event.name}
                </Text>
                <Text variant="meta" tone="muted" numberOfLines={1}>
                  {formatDateRange(event.startDate, event.endDate)} ·{' '}
                  {event.place}, {event.city}
                </Text>
              </View>
              <Text variant="displayS" tone="muted">
                ›
              </Text>
            </Pressable>
          );
        })}
      </View>
    </BottomSheet>
  );
}

const styles = StyleSheet.create({
  list: {gap: 10},
  row: {
    flexDirection: 'row',
    alignItems: 'center',
    gap: 12,
    borderWidth: 1,
    padding: 12,
    minHeight: 44,
  },
  bubble: {
    width: 40,
    height: 40,
    borderRadius: 20,
    borderWidth: 2,
    alignItems: 'center',
    justifyContent: 'center',
  },
  emoji: {fontSize: 18, lineHeight: 22},
  text: {flex: 1, gap: 2},
});
