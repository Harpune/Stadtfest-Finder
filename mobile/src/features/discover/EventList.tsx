/** List view of the discover screen (R03-US4): header, cards, endless scroll, refresh. */
import React from 'react';
import {
  FlatList,
  Pressable,
  RefreshControl,
  StyleSheet,
  View,
} from 'react-native';

import {
  EmptyState,
  EmptyStateProps,
  EventListCard,
  EventListCardSkeleton,
  Text,
} from '@/components';
import {strings} from '@/strings/de';
import {useTheme} from '@/theme';

import {formatDateRange} from '../events/dates';
import {eventStatus} from '../events/status';
import type {CategoryLook} from './categoryLookup';
import type {EventSummary} from './useDiscoverData';

export interface EventListProps {
  items: readonly EventSummary[];
  total: number | undefined;
  /** Place at the map center, e.g. "Aalen" ("um Aalen"). */
  areaName?: string;
  /** Switches to the map to move or zoom the area. */
  onChangeArea: () => void;
  today: string;
  categoryOf: (id: string) => CategoryLook;
  loading: boolean;
  refreshing: boolean;
  loadingMore: boolean;
  /** Shown instead of the cards when there is nothing to list. */
  empty?: EmptyStateProps;
  topInset: number;
  bottomInset: number;
  onRefresh: () => void;
  onEndReached: () => void;
  onOpen: (event: EventSummary) => void;
  onFavorite: (event: EventSummary) => void;
}

export function EventList({
  items,
  total,
  areaName,
  onChangeArea,
  today,
  categoryOf,
  loading,
  refreshing,
  loadingMore,
  empty,
  topInset,
  bottomInset,
  onRefresh,
  onEndReached,
  onOpen,
  onFavorite,
}: EventListProps) {
  const theme = useTheme();
  const showSkeleton = loading && items.length === 0;
  return (
    <FlatList
      testID="discover.list"
      data={showSkeleton ? [] : items}
      keyExtractor={item => item.id}
      style={{backgroundColor: theme.colors.background}}
      contentContainerStyle={[
        styles.content,
        {paddingTop: topInset, paddingBottom: bottomInset},
      ]}
      refreshControl={
        <RefreshControl
          refreshing={refreshing}
          onRefresh={onRefresh}
          tintColor={theme.colors.primary}
          progressViewOffset={topInset}
        />
      }
      onEndReachedThreshold={0.5}
      onEndReached={onEndReached}
      ListHeaderComponent={
        <View style={styles.header}>
          <View style={styles.headerRow}>
            <Text
              variant="displayM"
              testID="discover.list.header"
              style={styles.title}
            >
              {strings.discover.listHeader(total ?? items.length)}
            </Text>
            <Text variant="meta" tone="muted">
              {strings.discover.sortedByDate}
            </Text>
          </View>
          <View style={styles.areaRow}>
            {areaName ? (
              <Text
                variant="meta"
                tone="muted"
                numberOfLines={1}
                style={styles.area}
              >
                {strings.discover.listArea(areaName)}
              </Text>
            ) : null}
            <Pressable
              testID="discover.list.changeArea"
              accessibilityRole="button"
              onPress={onChangeArea}
              hitSlop={10}
            >
              <Text variant="meta" tone="primary" style={styles.link}>
                {strings.discover.changeArea}
              </Text>
            </Pressable>
          </View>
        </View>
      }
      ListEmptyComponent={
        showSkeleton ? (
          <View style={styles.skeletons}>
            <EventListCardSkeleton />
            <EventListCardSkeleton />
          </View>
        ) : empty ? (
          <EmptyState {...empty} />
        ) : null
      }
      ListFooterComponent={loadingMore ? <EventListCardSkeleton /> : null}
      renderItem={({item}) => {
        const status = eventStatus(item, today);
        const category = categoryOf(item.categoryId);
        return (
          <EventListCard
            testID={`discover.list.card.${item.id}`}
            name={item.name}
            statusLabel={status.label}
            statusTone={status.tone}
            dateRange={formatDateRange(item.startDate, item.endDate)}
            city={item.city}
            categoryName={category.name}
            emoji={category.emoji}
            distanceLabel={
              typeof item.distanceKm === 'number'
                ? strings.discover.distance(item.distanceKm)
                : undefined
            }
            onPress={() => onOpen(item)}
            onFavoritePress={() => onFavorite(item)}
          />
        );
      }}
    />
  );
}

const styles = StyleSheet.create({
  content: {paddingHorizontal: 16, gap: 16},
  header: {marginTop: 4, gap: 4},
  headerRow: {
    flexDirection: 'row',
    alignItems: 'baseline',
    justifyContent: 'space-between',
    gap: 12,
  },
  title: {flexShrink: 1},
  areaRow: {flexDirection: 'row', alignItems: 'center', gap: 10},
  area: {flexShrink: 1},
  link: {fontFamily: 'Outfit_600SemiBold'},
  skeletons: {gap: 16},
});
