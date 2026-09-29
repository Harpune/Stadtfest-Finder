/** Horizontal carousel over the map (R03-US3): snaps, swipe selects the centered event. */
import React, {useEffect, useRef} from 'react';
import {
  FlatList,
  NativeScrollEvent,
  NativeSyntheticEvent,
  StyleSheet,
  useWindowDimensions,
  View,
} from 'react-native';

import {
  CAROUSEL_CARD_HEIGHT,
  CAROUSEL_CARD_WIDTH,
  EventCarouselCard,
  EventCarouselCardSkeleton,
} from '@/components';
import {strings} from '@/strings/de';

import {formatDateRange} from '../events/dates';
import {eventStatus} from '../events/status';
import type {CategoryLook} from './categoryLookup';
import type {EventSummary} from './useDiscoverData';

const GAP = 12;
const ITEM = CAROUSEL_CARD_WIDTH + GAP;

export interface EventCarouselProps {
  items: readonly EventSummary[];
  loading: boolean;
  selectedId: string | null;
  today: string;
  categoryOf: (id: string) => CategoryLook;
  /** Swipe settled on an event. */
  onSettle: (event: EventSummary) => void;
  onPressCard: (event: EventSummary) => void;
}

export function EventCarousel({
  items,
  loading,
  selectedId,
  today,
  categoryOf,
  onSettle,
  onPressCard,
}: EventCarouselProps) {
  const {width} = useWindowDimensions();
  const listRef = useRef<FlatList<EventSummary>>(null);
  const side = Math.max(16, (width - CAROUSEL_CARD_WIDTH) / 2);
  const settledIndex = useRef(-1);

  // A marker tap scrolls the carousel to the matching card (R03-US2).
  useEffect(() => {
    const index = items.findIndex(item => item.id === selectedId);
    if (index >= 0 && index !== settledIndex.current) {
      settledIndex.current = index;
      listRef.current?.scrollToOffset({offset: index * ITEM, animated: true});
    }
  }, [selectedId, items]);

  if (loading && items.length === 0) {
    return (
      <View
        style={[styles.skeletonRow, {paddingLeft: side}]}
        testID="discover.carousel.loading"
      >
        <EventCarouselCardSkeleton />
        <EventCarouselCardSkeleton />
      </View>
    );
  }

  const onMomentumEnd = (event: NativeSyntheticEvent<NativeScrollEvent>) => {
    const index = Math.round(event.nativeEvent.contentOffset.x / ITEM);
    const item = items[Math.min(Math.max(index, 0), items.length - 1)];
    if (item && index !== settledIndex.current) {
      settledIndex.current = index;
      onSettle(item);
    }
  };

  return (
    <FlatList
      ref={listRef}
      testID="discover.carousel"
      horizontal
      data={items as EventSummary[]}
      keyExtractor={item => item.id}
      showsHorizontalScrollIndicator={false}
      snapToInterval={ITEM}
      decelerationRate="fast"
      contentContainerStyle={{paddingHorizontal: side, gap: GAP}}
      getItemLayout={(_, index) => ({
        length: ITEM,
        offset: ITEM * index,
        index,
      })}
      onMomentumScrollEnd={onMomentumEnd}
      style={styles.list}
      renderItem={({item}) => {
        const status = eventStatus(item, today);
        const category = categoryOf(item.categoryId);
        return (
          <EventCarouselCard
            testID={`discover.carousel.card.${item.id}`}
            name={item.name}
            statusLabel={status.label}
            statusTone={status.tone}
            dateRange={formatDateRange(item.startDate, item.endDate)}
            city={item.city}
            emoji={category.emoji}
            distanceLabel={
              typeof item.distanceKm === 'number'
                ? strings.discover.distance(item.distanceKm)
                : undefined
            }
            selected={item.id === selectedId}
            onPress={() => onPressCard(item)}
          />
        );
      }}
    />
  );
}

const styles = StyleSheet.create({
  list: {flexGrow: 0, height: CAROUSEL_CARD_HEIGHT + 24, overflow: 'visible'},
  skeletonRow: {
    flexDirection: 'row',
    gap: GAP,
    height: CAROUSEL_CARD_HEIGHT + 24,
  },
});
