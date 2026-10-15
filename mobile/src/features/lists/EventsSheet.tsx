/**
 * Add events to a list (R13-US4): own upcoming favorites first, a search over all public
 * events above (`GET /v1/events?q=`). Multiple choice; every tap takes effect at once.
 */
import React, {useMemo, useState} from 'react';
import {ActivityIndicator, StyleSheet, View} from 'react-native';

import {$api} from '@/api/client';
import {BottomSheet, CheckRow, Text, TextField} from '@/components';
import {buildCategoryLookup} from '@/features/discover/categoryLookup';
import {useCategories} from '@/features/discover/useDiscoverData';
import {useDebouncedValue} from '@/features/discover/useDebouncedValue';
import {formatDateRange, todayInBerlin} from '@/features/events/dates';
import {useFavorites} from '@/features/favorites/useFavorites';
import {strings} from '@/strings/de';

import type {ListEvent} from './useLists';

const s = strings.lists;

export function EventsSheet({
  visible,
  onClose,
  selected,
  onAdd,
  onRemove,
}: {
  visible: boolean;
  onClose: () => void;
  /** IDs of the events already in the list. */
  selected: ReadonlySet<string>;
  onAdd: (event: ListEvent) => void;
  onRemove: (eventId: string) => void;
}) {
  const [text, setText] = useState('');
  const q = useDebouncedValue(text.trim(), 300);
  const favorites = useFavorites();
  const categories = useCategories();
  const lookup = useMemo(
    () => buildCategoryLookup(categories.data),
    [categories.data],
  );
  const search = $api.useQuery(
    'get',
    '/v1/events',
    {params: {query: {q, limit: 20}}},
    {enabled: visible && q.length >= 2, staleTime: 60_000},
  );

  const today = todayInBerlin();
  const now = new Date().toISOString();
  const upcomingFavorites: ListEvent[] = (favorites.data?.items ?? [])
    .filter(f => f.endDate >= today)
    .map(f => ({...f, addedAt: now}));
  const results: ListEvent[] = (search.data?.items ?? []).map(e => {
    const category = lookup(e.categoryId);
    return {
      ...e,
      categoryName: category.name,
      emoji: category.emoji,
      addedAt: now,
    };
  });

  const row = (event: ListEvent, section: string) => {
    const checked = selected.has(event.id);
    return (
      <CheckRow
        key={`${section}-${event.id}`}
        label={event.name}
        meta={`${event.emoji} ${event.city} · ${formatDateRange(event.startDate, event.endDate)}`}
        checked={checked}
        onPress={() => (checked ? onRemove(event.id) : onAdd(event))}
        testID={`list.events.${section}.${event.id}`}
      />
    );
  };

  const searching = q.length >= 2;
  return (
    <BottomSheet
      visible={visible}
      onClose={onClose}
      title={s.eventsTitle}
      testID="list.events.sheet"
    >
      <TextField
        label={s.searchPlaceholder}
        hideLabel
        placeholder={s.searchPlaceholder}
        value={text}
        onChangeText={setText}
        testID="list.events.search"
      />
      {searching ? (
        <View>
          <Text variant="label">{s.results}</Text>
          {search.isPending ? (
            <ActivityIndicator style={styles.loading} />
          ) : null}
          {search.isSuccess && results.length === 0 ? (
            <Text variant="meta" tone="muted" style={styles.hint}>
              {s.noResults}
            </Text>
          ) : null}
          {results.map(event => row(event, 'result'))}
        </View>
      ) : (
        <View>
          <Text variant="label">{s.favorites}</Text>
          {upcomingFavorites.map(event => row(event, 'favorite'))}
        </View>
      )}
    </BottomSheet>
  );
}

const styles = StyleSheet.create({
  loading: {marginTop: 12},
  hint: {marginTop: 8},
});
