/** List view of the discover screen (R03-US4): header, cards, endless scroll, refresh. */
import React from 'react';
import {FlatList, RefreshControl, StyleSheet, View} from 'react-native';

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
  radiusKm: number;
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
  radiusKm,
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
          <Text variant="displayM" testID="discover.list.header">
            {strings.discover.listHeader(total ?? items.length, radiusKm)}
          </Text>
          <Text variant="meta" tone="muted">
            {strings.discover.sortedByDate}
          </Text>
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
  header: {
    flexDirection: 'row',
    alignItems: 'baseline',
    justifyContent: 'space-between',
    marginTop: 4,
  },
  skeletons: {gap: 16},
});
