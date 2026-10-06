/**
 * "Entdecken" (R03): map and list of events with search, category chips and filter sheet.
 * Map and list share one query; the map stays mounted below the list, so switching views
 * keeps search, filter, selection and camera without reloading.
 */
import {router} from 'expo-router';
import React, {useCallback, useEffect, useMemo, useRef, useState} from 'react';
import {Keyboard, StyleSheet, View} from 'react-native';
import {useSafeAreaInsets} from 'react-native-safe-area-context';

import {
  AvatarButton,
  Chip,
  ChipRow,
  EmptyState,
  EmptyStateProps,
  FilterButton,
  FilterSheet,
  LoadingPill,
  MapControls,
  PlaceSuggestion,
  SearchBar,
  SegmentedToggle,
  Text,
  useToast,
} from '@/components';
import {strings} from '@/strings/de';
import {useTheme} from '@/theme';

import {ProfileDrawer} from '../account/ProfileDrawer';
import {initialsOf, useAuth} from '../auth/AuthProvider';
import {useUnreadCount} from '../notifications/useNotifications';
import {todayInBerlin} from '../events/dates';
import {
  favoriteEntryFrom,
  useFavoriteIds,
  useToggleFavorite,
} from '../favorites/useFavorites';
import {buildCategoryLookup} from './categoryLookup';
import {
  DiscoverMap,
  DiscoverMapHandle,
  LOCATED_ZOOM,
  MapViewport,
} from './DiscoverMap';
import {useDiscover} from './DiscoverProvider';
import {EventList} from './EventList';
import {EventStackSheet} from './EventStackSheet';
import {
  activeFilterCount,
  DiscoverFilter,
  effectiveTime,
  monthOptions,
  pruneMonths,
  toQueryParams,
} from './filter';
import {inBbox, roundedDistanceKm, searchArea} from './geo';
import {HAS_TILE_KEY} from './mapStyle';
import {
  loadCamera,
  loadLastSearch,
  saveCamera,
  saveLastSearch,
  StoredCamera,
  StoredSearch,
} from './persistence';
import {useDebouncedValue} from './useDebouncedValue';
import {
  EventSummary,
  SEARCH_PAGE_SIZE,
  useCategories,
  useEventCount,
  useAreaName,
  useEventSearch,
  usePlaceSuggestion,
} from './useDiscoverData';
import {useUserLocation} from './useUserLocation';

/** Germany center, used without location access and without a stored camera (R03-US1). */
const GERMANY: StoredCamera = {center: [10.45, 51.16], zoom: 6};
const DEBOUNCE_MS = 300;
/** Zoom after "Zu {Ort} springen": a town and its surroundings. */
const PLACE_ZOOM = 11;
/** How long the start waits for a first GPS fix before using the fallback camera. */
const START_FIX_WAIT_MS = 3000;
const VIEW_OPTIONS = [
  {value: 'map', label: strings.discover.map, icon: 'map'},
  {value: 'list', label: strings.discover.list, icon: 'list'},
] as const;

function timeChipLabel(filter: DiscoverFilter): string {
  switch (effectiveTime(filter)) {
    case 'all':
      return strings.filter.timeAll;
    case 'today':
      return strings.filter.timeToday;
    case 'weekend':
      return strings.filter.timeWeekend;
    case 'months':
      return strings.filter.monthsChip(filter.months.length);
  }
}

export function DiscoverScreen() {
  const theme = useTheme();
  const insets = useSafeAreaInsets();
  const toast = useToast();
  const {state, dispatch} = useDiscover();
  const {location, locate} = useUserLocation();
  const {requestAccountAction, user} = useAuth();
  const unread = useUnreadCount();
  const [drawerOpen, setDrawerOpen] = useState(false);
  const mapRef = useRef<DiscoverMapHandle>(null);
  const today = todayInBerlin();

  // ---- start camera: position (zoom 10), else last stored camera, else Germany -------------
  // Wait briefly for a first GPS fix; never block the screen on it (R03-US1).
  const [startCamera, setStartCamera] = useState<StoredCamera | null>(null);
  const [fixTimedOut, setFixTimedOut] = useState(false);
  useEffect(() => {
    const timer = setTimeout(() => setFixTimedOut(true), START_FIX_WAIT_MS);
    return () => clearTimeout(timer);
  }, []);
  useEffect(() => {
    if (startCamera) return;
    if (location.status === 'granted' && location.position) {
      const {lat, lon} = location.position;
      setStartCamera({center: [lon, lat], zoom: LOCATED_ZOOM});
    } else if (
      fixTimedOut || // permission dialog or GPS fix still pending: start anyway
      location.status === 'denied' ||
      (location.status === 'granted' && !location.locating)
    ) {
      void loadCamera().then(stored => setStartCamera(stored ?? GERMANY));
    }
  }, [location, startCamera, fixTimedOut]);

  const position = location.status === 'granted' ? location.position : null;

  // A fix that arrives after the map started elsewhere moves the map there once.
  const flewToFix = useRef(false);
  useEffect(() => {
    if (!position || !startCamera || flewToFix.current) return;
    flewToFix.current = true;
    const [lon, lat] = startCamera.center;
    if (lon !== position.lon || lat !== position.lat) {
      mapRef.current?.flyTo(position, LOCATED_ZOOM);
    }
  }, [position, startCamera]);

  // ---- viewport and query -------------------------------------------------------------
  const [viewport, setViewport] = useState<MapViewport | null>(null);
  const debouncedViewport = useDebouncedValue(viewport, DEBOUNCE_MS);
  const debouncedQuery = useDebouncedValue(state.query, DEBOUNCE_MS);
  const onViewportChange = useCallback(
    (next: MapViewport) => {
      setViewport(next);
      // Only without location access: the camera is then not the user's position.
      if (!position) {
        void saveCamera({
          center: [next.center.lon, next.center.lat],
          zoom: next.zoom,
        });
      }
    },
    [position],
  );

  // The visible map area is the only spatial filter (no radius). The search loads a padded,
  // grid-snapped area so small pans hit the cache; the list shows the visible part.
  const bbox = debouncedViewport?.bbox;
  const searchParams = useMemo(
    () =>
      toQueryParams(
        pruneMonths(state.filter, today),
        bbox ? searchArea(bbox) : undefined,
        debouncedQuery,
      ),
    [state.filter, today, bbox, debouncedQuery],
  );
  const countParams = useMemo(
    () => toQueryParams(pruneMonths(state.filter, today), bbox, debouncedQuery),
    [state.filter, today, bbox, debouncedQuery],
  );
  const ready = debouncedViewport !== null;

  const categories = useCategories();
  const search = useEventSearch(searchParams, ready);
  const counts = useEventCount(countParams, ready);
  const categoryOf = useMemo(
    () => buildCategoryLookup(categories.data),
    [categories.data],
  );

  const favoriteIds = useFavoriteIds();
  const toggle = useToggleFavorite();
  const toggleFavorite = (event: EventSummary) => {
    if (!requestAccountAction({type: 'favorite', eventId: event.id})) return;
    void toggle(
      favoriteEntryFrom(event, categoryOf(event.categoryId)),
      !favoriteIds.has(event.id),
    );
  };

  // Selected categories that were deactivated disappear silently (R03-US6).
  useEffect(() => {
    if (categories.data) {
      dispatch({
        type: 'pruneCategories',
        activeCategoryIds: categories.data.map(c => c.id),
      });
    }
  }, [categories.data, dispatch]);

  // ---- offline fallback (R03-US8) ------------------------------------------------------
  const [offline, setOffline] = useState<StoredSearch | null>(null);
  useEffect(() => {
    if (search.isSuccess && !search.isPlaceholderData) {
      setOffline(null);
      void saveLastSearch(search.items);
    }
  }, [search.isSuccess, search.isPlaceholderData, search.items]);

  const retry = search.refetch;
  useEffect(() => {
    if (!search.isError) return;
    if (search.items.length === 0) {
      void loadLastSearch().then(setOffline);
    }
    toast(strings.discover.loadFailed, {
      action: {label: strings.common.retry, onPress: () => void retry()},
    });
    // Runs once per new error, not on re-renders with a new toast/retry reference.
  }, [search.isError, search.errorUpdatedAt]);

  // Distances are computed on the device from the own position, else from the map center.
  const distanceFrom = position ?? debouncedViewport?.center ?? null;
  const loadedItems = useMemo<EventSummary[]>(() => {
    const raw = search.items.length > 0 ? search.items : (offline?.items ?? []);
    return raw.map(item => ({
      ...item,
      distanceKm: distanceFrom ? roundedDistanceKm(distanceFrom, item) : null,
    }));
  }, [search.items, offline, distanceFrom]);
  const items = useMemo(
    () => (bbox ? loadedItems.filter(item => inBbox(item, bbox)) : loadedItems),
    [loadedItems, bbox],
  );
  const loading = !ready || (search.isFetching && !search.isFetchingNextPage);
  const firstLoad = !ready || (search.isPending && items.length === 0);

  // ---- selection ------------------------------------------------------------------------
  const selectOrOpen = useCallback(
    (event: EventSummary) => {
      if (state.selectedEventId === event.id) {
        router.push(`/f/${event.id}`);
      } else {
        dispatch({type: 'select', eventId: event.id});
      }
    },
    [state.selectedEventId, dispatch],
  );
  // Festivals at the same spot (cluster that zooming cannot split) as a list.
  const [stack, setStack] = useState<EventSummary[] | null>(null);
  const clearSelection = useCallback(() => {
    if (state.selectedEventId) dispatch({type: 'select', eventId: null});
  }, [state.selectedEventId, dispatch]);

  // ---- filter sheet ---------------------------------------------------------------------
  const [sheetOpen, setSheetOpen] = useState(false);
  const [draft, setDraft] = useState<DiscoverFilter>(state.filter);
  const debouncedDraft = useDebouncedValue(draft, DEBOUNCE_MS);
  const draftParams = useMemo(
    () => toQueryParams(debouncedDraft, bbox, debouncedQuery),
    [debouncedDraft, bbox, debouncedQuery],
  );
  const draftCount = useEventCount(draftParams, sheetOpen && ready);
  const months = useMemo(() => monthOptions(today), [today]);

  // ---- empty states ---------------------------------------------------------------------
  const resetAll = () => dispatch({type: 'resetAll'});
  const showEmpty =
    ready &&
    search.isSuccess &&
    !search.isPlaceholderData &&
    items.length === 0;
  const empty: EmptyStateProps | undefined = showEmpty
    ? debouncedQuery.trim().length >= 2
      ? {
          testID: 'discover.empty.search',
          title: strings.discover.noResultsTitle(debouncedQuery.trim()),
          text: strings.discover.noResultsText,
          secondary: {
            label: strings.discover.resetFilters,
            onPress: resetAll,
            testID: 'discover.empty.reset',
          },
        }
      : {
          testID: 'discover.empty.area',
          title: strings.discover.emptyTitle,
          text: strings.discover.emptyText,
          primary: {
            label: strings.discover.zoomOut,
            onPress: () => mapRef.current?.zoomBy(-2),
            testID: 'discover.empty.zoomOut',
          },
          secondary: {
            label: strings.discover.resetFilters,
            onPress: resetAll,
            testID: 'discover.empty.reset',
          },
        }
    : undefined;

  const statusPill = firstLoad
    ? strings.discover.loadingEvents
    : offline && search.items.length === 0
      ? strings.discover.offline(
          new Date(offline.savedAt).toLocaleTimeString('de-DE', {
            hour: '2-digit',
            minute: '2-digit',
          }),
        )
      : search.items.length >= SEARCH_PAGE_SIZE
        ? strings.discover.zoomIn
        : null;

  // ---- list header and place suggestion ------------------------------------------------
  const isListView = state.view === 'list';
  const areaName = useAreaName(debouncedViewport?.center ?? null, isListView);
  const place = usePlaceSuggestion(state.query.trim() ? debouncedQuery : '');
  const jumpToPlace = () => {
    if (!place) return;
    Keyboard.dismiss();
    mapRef.current?.flyTo({lat: place.lat, lon: place.lon}, PLACE_ZOOM);
    // The search text named the place, not an event: show all events there.
    dispatch({type: 'setQuery', query: ''});
  };

  // ---- layout -----------------------------------------------------------------------------
  const isList = state.view === 'list';
  const headerTop = insets.top + 8;
  const toggleBottom = insets.bottom + 6;
  const controlsBottom = toggleBottom + 48 + 10;
  const headerHeight = 50 + 12 + 50 + (place ? 52 : 0);

  return (
    <View
      style={[styles.root, {backgroundColor: theme.colors.background}]}
      testID="discover.screen"
    >
      {startCamera ? (
        <DiscoverMap
          ref={mapRef}
          initialCenter={{
            lon: startCamera.center[0],
            lat: startCamera.center[1],
          }}
          initialZoom={startCamera.zoom}
          items={loadedItems}
          selectedId={state.selectedEventId}
          categoryOf={categoryOf}
          showUserLocation={position !== null}
          onViewportChange={onViewportChange}
          onMarkerPress={selectOrOpen}
          onStackPress={setStack}
          onMapPress={clearSelection}
        />
      ) : null}

      {isList ? (
        <View style={StyleSheet.absoluteFill}>
          <EventList
            items={items}
            total={counts.data?.total}
            areaName={areaName.data?.city}
            onChangeArea={() => dispatch({type: 'setView', view: 'map'})}
            today={today}
            categoryOf={categoryOf}
            loading={firstLoad}
            refreshing={search.isRefetching && !search.isPlaceholderData}
            loadingMore={search.isFetchingNextPage}
            empty={empty}
            topInset={headerTop + headerHeight + 16}
            bottomInset={toggleBottom + 72}
            onRefresh={() => void search.refetch()}
            onEndReached={() => {
              if (search.hasNextPage) void search.fetchNextPage();
            }}
            onOpen={event => router.push(`/f/${event.id}`)}
            onFavorite={toggleFavorite}
            favoriteIds={favoriteIds}
          />
        </View>
      ) : (
        <>
          <View
            style={[styles.bottom, {bottom: controlsBottom}]}
            pointerEvents="box-none"
          >
            {/* Attribution (left) and map controls (right) sit above the view toggle or the
                empty-state card, so they never overlap it. A tapped pin shows name and date
                itself; there is no carousel (decision 01.10.2026). */}
            <View style={styles.aboveCards} pointerEvents="box-none">
              {HAS_TILE_KEY ? (
                <Text
                  variant="micro"
                  tone="muted"
                  testID="discover.attribution"
                  style={styles.attribution}
                >
                  {strings.discover.attribution}
                </Text>
              ) : (
                <View />
              )}
              <MapControls
                onZoomIn={() => mapRef.current?.zoomBy(1)}
                onZoomOut={() => mapRef.current?.zoomBy(-1)}
                onLocate={
                  location.status === 'granted'
                    ? async () => {
                        const next = await locate();
                        if (next) mapRef.current?.flyTo(next, LOCATED_ZOOM);
                      }
                    : undefined
                }
              />
            </View>
            {empty ? (
              <View style={styles.emptyWrap}>
                <EmptyState {...empty} />
              </View>
            ) : null}
          </View>
          {statusPill ? (
            <View
              style={[styles.pill, {top: headerTop + headerHeight + 12}]}
              pointerEvents="none"
            >
              <LoadingPill
                label={statusPill}
                spinner={firstLoad || loading}
                testID="discover.status"
              />
            </View>
          ) : null}
        </>
      )}

      {/* Floating header: search, filter, profile, chips. Opaque in the list view. */}
      <View
        style={[
          styles.header,
          {paddingTop: headerTop},
          isList && {
            backgroundColor: theme.colors.background,
            borderBottomColor: theme.colors.outline,
            borderBottomWidth: 1,
          },
        ]}
        pointerEvents="box-none"
      >
        <View style={styles.searchRow}>
          <SearchBar
            value={state.query}
            onChangeText={query => dispatch({type: 'setQuery', query})}
            testID="discover.search.input"
            variant={isList ? 'surface' : 'floating'}
            trailing={
              <FilterButton
                activeCount={activeFilterCount(state.filter)}
                onPress={() => setSheetOpen(true)}
                testID="discover.filter.open"
              />
            }
          />
          <AvatarButton
            onPress={() => setDrawerOpen(true)}
            initials={initialsOf(user) || undefined}
            hasUnread={unread > 0}
            testID="discover.profile"
          />
        </View>
        {place ? (
          <View style={styles.suggestion}>
            <PlaceSuggestion
              label={strings.discover.jumpTo(place.label)}
              onPress={jumpToPlace}
              testID="discover.place.jump"
            />
          </View>
        ) : null}
        <ChipRow testID="discover.chips">
          <Chip
            label={timeChipLabel(state.filter)}
            dropdown
            active={effectiveTime(state.filter) !== 'all'}
            onPress={() => setSheetOpen(true)}
            testID="discover.chip.time"
          />
          {(categories.data ?? []).map(category => (
            <Chip
              key={category.id}
              label={category.name}
              emoji={category.emoji}
              count={counts.data?.byCategory[category.id] ?? 0}
              active={state.filter.categoryIds.includes(category.id)}
              onPress={() =>
                dispatch({type: 'toggleCategory', categoryId: category.id})
              }
              testID={`discover.chip.${category.id}`}
            />
          ))}
        </ChipRow>
      </View>

      <View
        style={[styles.toggle, {bottom: toggleBottom}]}
        pointerEvents="box-none"
      >
        <SegmentedToggle
          options={VIEW_OPTIONS}
          value={state.view}
          onChange={view => dispatch({type: 'setView', view})}
          testID="discover.toggle"
        />
      </View>

      <EventStackSheet
        events={stack}
        today={today}
        categoryOf={categoryOf}
        onOpen={event => {
          setStack(null);
          router.push(`/f/${event.id}`);
        }}
        onClose={() => setStack(null)}
      />

      <FilterSheet
        visible={sheetOpen}
        filter={state.filter}
        categories={categories.data ?? []}
        monthOptions={months}
        previewCount={draftCount.data?.total}
        previewLoading={draftCount.isFetching}
        onDraftChange={setDraft}
        onApply={filter => {
          dispatch({type: 'applyFilter', filter});
          setSheetOpen(false);
        }}
        onClose={() => setSheetOpen(false)}
      />
      <ProfileDrawer
        visible={drawerOpen}
        onClose={() => setDrawerOpen(false)}
      />
    </View>
  );
}

const styles = StyleSheet.create({
  root: {flex: 1},
  header: {
    position: 'absolute',
    top: 0,
    left: 0,
    right: 0,
    gap: 6,
    paddingBottom: 6,
  },
  searchRow: {
    flexDirection: 'row',
    alignItems: 'center',
    gap: 10,
    paddingHorizontal: 16,
  },
  bottom: {position: 'absolute', left: 0, right: 0},
  suggestion: {paddingHorizontal: 16},
  emptyWrap: {paddingHorizontal: 16},
  pill: {position: 'absolute', left: 0, right: 0, alignItems: 'center'},
  toggle: {position: 'absolute', left: 0, right: 0, alignItems: 'center'},
  aboveCards: {
    flexDirection: 'row',
    justifyContent: 'space-between',
    alignItems: 'flex-end',
    paddingHorizontal: 16,
    marginBottom: 8,
  },
  attribution: {flexShrink: 1, marginRight: 12, marginBottom: 2},
});
