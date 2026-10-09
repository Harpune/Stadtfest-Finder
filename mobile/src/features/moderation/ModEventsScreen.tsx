/**
 * Overview of all events (R07-US2, 08-01, no regions since ADR 0015): search and status chips filter the
 * loaded list on the device; a row opens the form.
 */
import React, {useEffect, useMemo, useState} from 'react';
import {FlatList, StyleSheet, View} from 'react-native';

import {
  AiSearchBanner,
  Button,
  ChipRow,
  Chip,
  EmptyState,
  ModEventRow,
  ModEventRowSkeleton,
  SearchBar,
  Text,
} from '@/components';
import {navigate} from '@/features/navigation/navigate';
import {buildCategoryLookup} from '@/features/discover/categoryLookup';
import {useCategories} from '@/features/discover/useDiscoverData';
import {
  formatDateRange,
  monthShort,
  parseIsoDate,
} from '@/features/events/dates';
import {strings} from '@/strings/de';
import {useTheme} from '@/theme';

import {AiSearch, useAiSearch} from './ai/AiSearchProvider';
import {AiSearchSheet} from './ai/AiSearchSheet';
import {
  ModEventSummary,
  useExitModeration,
  useModEvents,
} from './useModeration';

type StatusFilter = 'all' | ModEventSummary['status'];
const FILTERS: readonly StatusFilter[] = [
  'all',
  'draft',
  'published',
  'past',
  'cancelled',
];

function matches(event: ModEventSummary, query: string): boolean {
  const needle = query.trim().toLocaleLowerCase('de');
  if (!needle) return true;
  return `${event.name} ${event.place} ${event.city}`
    .toLocaleLowerCase('de')
    .includes(needle);
}

function yearOf(iso: string): number {
  return parseIsoDate(iso).year;
}

export function ModEventsScreen() {
  const theme = useTheme();
  const events = useModEvents();
  const categories = useCategories();
  const exit = useExitModeration();
  const [query, setQuery] = useState('');
  const [filter, setFilter] = useState<StatusFilter>('all');
  const [sheetOpen, setSheetOpen] = useState(false);
  const ai = useAiSearch();
  const categoryOf = buildCategoryLookup(categories.data);

  // The role was taken away meanwhile: back to the user view (R07-US1).
  const status = (events.error as {status?: number} | null)?.status;
  const forbidden =
    events.isError &&
    (status === 403 ||
      (events.error as {error?: string} | null)?.error === 'forbidden');
  useEffect(() => {
    if (forbidden) exit(strings.mod.forbidden);
  }, [forbidden, exit]);

  const items = events.data?.items;
  const searched = useMemo(
    () => (items ?? []).filter(event => matches(event, query)),
    [items, query],
  );
  const counts = useMemo(() => {
    const result: Record<StatusFilter, number> = {
      all: searched.length,
      draft: 0,
      published: 0,
      past: 0,
      cancelled: 0,
    };
    for (const event of searched) result[event.status] += 1;
    return result;
  }, [searched]);
  const visible =
    filter === 'all'
      ? searched
      : searched.filter(event => event.status === filter);

  const header = (
    <View style={styles.header}>
      <View style={styles.titleRow}>
        <Text variant="displayXL" style={styles.title}>
          {strings.mod.title}
        </Text>
        <Button
          label={strings.mod.ai.searchButton}
          variant="modOutline"
          size="medium"
          onPress={() => setSheetOpen(true)}
          testID="mod.events.aiSearch"
        />
        <Button
          label={strings.mod.newEvent}
          variant="mod"
          size="medium"
          onPress={() => navigate('/mod/fest/neu')}
          testID="mod.events.new"
        />
      </View>
      <SearchBar
        value={query}
        onChangeText={setQuery}
        placeholder={strings.mod.searchPlaceholder}
        variant="surface"
        testID="mod.events.search"
      />
      {ai.search ? (
        <SearchStatus
          search={ai.search}
          onDismiss={ai.dismiss}
          onRetry={() => void ai.start(ai.search?.postalCode ?? '')}
        />
      ) : null}
      <ChipRow testID="mod.events.filters">
        {FILTERS.map(key => (
          <Chip
            key={key}
            label={
              key === 'all' ? strings.mod.filterAll : strings.mod.status[key]
            }
            count={counts[key]}
            active={filter === key}
            accent="mod"
            variant="sheet"
            onPress={() => setFilter(key)}
            testID={`mod.events.filter.${key}`}
          />
        ))}
      </ChipRow>
    </View>
  );

  return (
    <>
      <AiSearchSheet visible={sheetOpen} onClose={() => setSheetOpen(false)} />
      <FlatList
        testID="mod.events"
        data={items ? visible : []}
        keyExtractor={event => event.id}
        contentContainerStyle={styles.content}
        style={{backgroundColor: theme.colors.background}}
        ListHeaderComponent={header}
        refreshing={events.isRefetching}
        onRefresh={() => void events.refetch()}
        renderItem={({item}) => {
          const category = item.categoryId
            ? categoryOf(item.categoryId)
            : undefined;
          const start = item.startDate ? parseIsoDate(item.startDate) : null;
          const range =
            item.startDate && item.endDate
              ? `${formatDateRange(item.startDate, item.endDate)} ${yearOf(item.endDate)}`
              : '';
          const meta = [
            `${category?.emoji ?? '📍'} ${item.city || item.place || '–'}`,
            range,
          ]
            .filter(Boolean)
            .join(' · ');
          return (
            <ModEventRow
              name={item.name}
              status={item.status}
              day={start ? String(start.day) : '–'}
              month={start ? monthShort(start.month).toUpperCase() : ''}
              meta={meta}
              favoriteCount={item.favoriteCount}
              autoFound={item.source === 'ai'}
              onPress={() => navigate(`/mod/fest/${item.id}`)}
              testID={`mod.events.row.${item.id}`}
            />
          );
        }}
        ListEmptyComponent={
          events.isPending ? (
            <View style={styles.list}>
              {[0, 1, 2].map(i => (
                <ModEventRowSkeleton key={i} />
              ))}
            </View>
          ) : events.isError && !forbidden ? (
            <EmptyState
              title={strings.mod.loadFailed}
              text=""
              primary={{
                label: strings.mod.retry,
                onPress: () => void events.refetch(),
                testID: 'mod.events.retry',
              }}
              testID="mod.events.error"
            />
          ) : (
            <EmptyState
              title={strings.mod.emptyTitle}
              text={strings.mod.emptyText}
              testID="mod.events.empty"
            />
          )
        }
      />
    </>
  );
}

const styles = StyleSheet.create({
  content: {padding: 16, gap: 12, paddingBottom: 32},
  header: {gap: 14, marginBottom: 4},
  titleRow: {flexDirection: 'row', alignItems: 'center', gap: 12},
  title: {flex: 1},
  list: {gap: 12},
});

/** Status bar of the AI search (09-02, 09-03). */
function SearchStatus({
  search,
  onDismiss,
  onRetry,
}: {
  search: AiSearch;
  onDismiss: () => void;
  onRetry: () => void;
}) {
  if (search.status === 'queued' || search.status === 'running') {
    return (
      <AiSearchBanner
        state="running"
        text={strings.mod.ai.running(search.postalCode, search.placeName)}
        testID="mod.ai.banner"
      />
    );
  }
  if (search.status === 'failed') {
    return (
      <AiSearchBanner
        state="failed"
        text={strings.mod.ai.failed}
        onRetry={onRetry}
        onDismiss={onDismiss}
        testID="mod.ai.banner"
      />
    );
  }
  const found = search.newEventIds.length;
  return found > 0 ? (
    <AiSearchBanner
      state="found"
      text={strings.mod.ai.found(found, search.postalCode)}
      onReview={() => navigate(`/mod/pruefen/${search.id}`)}
      onDismiss={onDismiss}
      testID="mod.ai.banner"
    />
  ) : (
    <AiSearchBanner
      state="nothing"
      text={strings.mod.ai.nothing(search.postalCode, search.skipped.duplicate)}
      onDismiss={onDismiss}
      testID="mod.ai.banner"
    />
  );
}
