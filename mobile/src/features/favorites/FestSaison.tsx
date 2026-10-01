/**
 * "Deine Festsaison" in the profile drawer (R06-US3): timeline of the favorites grouped by
 * month, the running festival highlighted, past ones on request, and the empty state.
 */
import React, {useState} from 'react';
import {Pressable, StyleSheet, View} from 'react-native';

import {Button, Icon, Skeleton, Text} from '@/components';
import {
  formatDateRange,
  formatWeekdayDate,
  IsoDate,
} from '@/features/events/dates';
import {eventStatus} from '@/features/events/status';
import {strings} from '@/strings/de';
import {useTheme} from '@/theme';

import {buildTimeline, FavoriteEntry, MonthGroup} from './timeline';

export interface FestSaisonProps {
  favorites: FavoriteEntry[] | undefined;
  loading: boolean;
  error: boolean;
  today: IsoDate;
  onOpen: (eventId: string) => void;
  onDiscover: () => void;
  onRetry: () => void;
}

const LINE_X = 5;
const INDENT = 24;

export function FestSaison({
  favorites,
  loading,
  error,
  today,
  onOpen,
  onDiscover,
  onRetry,
}: FestSaisonProps) {
  const [showPast, setShowPast] = useState(false);

  if (!favorites) {
    if (error && !loading) {
      return (
        <View style={styles.section} testID="favorites.error">
          <Text variant="displayL">{strings.drawer.title}</Text>
          <Text variant="body" tone="muted">
            {strings.drawer.loadFailed}
          </Text>
          <Button
            label={strings.drawer.retry}
            variant="secondary"
            onPress={onRetry}
            testID="favorites.retry"
          />
        </View>
      );
    }
    return (
      <View style={styles.section} testID="favorites.loading">
        <Text variant="displayL">{strings.drawer.title}</Text>
        <Skeleton width="50%" height={16} />
        {[0, 1, 2].map(i => (
          <View key={i} style={styles.skeletonRow}>
            <Skeleton width="40%" height={13} />
            <Skeleton width="85%" height={20} />
          </View>
        ))}
      </View>
    );
  }

  const timeline = buildTimeline(favorites, today);
  if (timeline.pastCount + timeline.upcomingCount === 0) {
    return (
      <View style={styles.section}>
        <Text variant="displayL">{strings.drawer.title}</Text>
        <EmptyTimeline onDiscover={onDiscover} />
      </View>
    );
  }

  return (
    <View style={styles.section}>
      <Text variant="displayL">{strings.drawer.title}</Text>
      <Text variant="body" tone="muted" testID="favorites.count">
        {strings.drawer.upcoming(timeline.upcomingCount)}
      </Text>
      {timeline.pastCount > 0 ? (
        <PastToggle
          label={
            showPast
              ? strings.drawer.hidePast
              : strings.drawer.showPast(timeline.pastCount)
          }
          onPress={() => setShowPast(value => !value)}
        />
      ) : null}
      <TimelineLine>
        {showPast ? (
          <>
            {timeline.past.map(group => (
              <MonthBlock
                key={`past-${group.title}`}
                group={group}
                past
                today={today}
                onOpen={onOpen}
              />
            ))}
            <TodayMarker today={today} />
          </>
        ) : null}
        {timeline.upcoming.map(group => (
          <MonthBlock
            key={group.title}
            group={group}
            past={false}
            today={today}
            onOpen={onOpen}
          />
        ))}
      </TimelineLine>
    </View>
  );
}

function PastToggle({label, onPress}: {label: string; onPress: () => void}) {
  const theme = useTheme();
  return (
    <Pressable
      testID="favorites.togglePast"
      accessibilityRole="button"
      onPress={onPress}
      style={({pressed}) => [
        styles.pastToggle,
        {
          backgroundColor: theme.colors.surfaceVariant,
          opacity: pressed ? 0.8 : 1,
        },
      ]}
    >
      <Text variant="bodyStrong" tone="muted">
        {label}
      </Text>
    </Pressable>
  );
}

function TimelineLine({children}: {children: React.ReactNode}) {
  const theme = useTheme();
  return (
    <View style={styles.timeline}>
      <View
        style={[styles.line, {backgroundColor: theme.colors.outline}]}
        accessibilityElementsHidden
      />
      {children}
    </View>
  );
}

function MonthBlock({
  group,
  past,
  today,
  onOpen,
}: {
  group: MonthGroup;
  past: boolean;
  today: IsoDate;
  onOpen: (eventId: string) => void;
}) {
  const theme = useTheme();
  return (
    <View style={styles.month}>
      <Text
        variant="displayS"
        style={[
          styles.monthTitle,
          {color: past ? theme.colors.onSurfaceFaint : theme.colors.secondary},
        ]}
        accessibilityRole="header"
      >
        {group.title}
      </Text>
      {group.entries.map(entry => (
        <TimelineEntry
          key={entry.id}
          entry={entry}
          past={past}
          today={today}
          onOpen={onOpen}
        />
      ))}
    </View>
  );
}

function TimelineEntry({
  entry,
  past,
  today,
  onOpen,
}: {
  entry: FavoriteEntry;
  past: boolean;
  today: IsoDate;
  onOpen: (eventId: string) => void;
}) {
  const theme = useTheme();
  const c = theme.colors;
  const status = eventStatus(entry, today);
  const dateRange = formatDateRange(entry.startDate, entry.endDate);
  const testID = `favorites.entry.${entry.id}`;

  if (status.tone === 'running' && !past) {
    return (
      <Pressable
        testID={testID}
        accessibilityRole="button"
        accessibilityLabel={`${entry.name}, ${status.label}`}
        onPress={() => onOpen(entry.id)}
        style={({pressed}) => [styles.entry, {opacity: pressed ? 0.85 : 1}]}
      >
        <View
          style={[
            styles.runningDot,
            {backgroundColor: c.primary, shadowColor: c.primary},
          ]}
        />
        <View
          style={[
            styles.runningCard,
            {
              backgroundColor: c.primaryContainer,
              borderColor: c.primary,
              borderRadius: theme.radius.card,
            },
          ]}
        >
          <Text variant="bodyStrong" tone="primary">
            ● {status.label}
          </Text>
          <Text variant="displayS" style={styles.name}>
            {entry.name}
          </Text>
          <Text variant="meta" tone="muted" numberOfLines={1}>
            {dateRange} · {entry.emoji} {entry.city}
          </Text>
        </View>
      </Pressable>
    );
  }

  const cancelled = entry.status === 'cancelled';
  const dateLine = past
    ? `${dateRange} · ${strings.drawer.past}`
    : cancelled
      ? `${dateRange} · ${status.label}`
      : dateRange;
  return (
    <Pressable
      testID={testID}
      accessibilityRole="button"
      accessibilityLabel={`${entry.name}, ${dateLine}`}
      onPress={() => onOpen(entry.id)}
      style={({pressed}) => [styles.entry, {opacity: pressed ? 0.7 : 1}]}
    >
      <View
        style={[
          styles.dot,
          past
            ? {backgroundColor: c.outline, borderColor: c.outline}
            : {borderColor: c.secondary, backgroundColor: c.background},
        ]}
      />
      <View style={styles.entryText}>
        <Text
          variant="meta"
          tone={past ? 'faint' : cancelled ? 'error' : 'muted'}
        >
          {dateLine}
        </Text>
        <Text
          variant="displayS"
          tone={past ? 'faint' : 'default'}
          style={styles.name}
        >
          {entry.name}
        </Text>
        <Text variant="meta" tone={past ? 'faint' : 'muted'} numberOfLines={1}>
          {past
            ? `${entry.emoji} ${entry.city}`
            : `${entry.emoji} ${entry.categoryName} · ${entry.city}`}
        </Text>
      </View>
    </Pressable>
  );
}

function TodayMarker({today}: {today: IsoDate}) {
  const theme = useTheme();
  const pink = theme.colors.secondary;
  return (
    <View style={styles.today} testID="favorites.today">
      <View style={[styles.todayDash, {backgroundColor: pink}]} />
      <Text variant="label" style={{color: pink}}>
        {strings.drawer.today(formatWeekdayDate(today))}
      </Text>
      <View
        style={[styles.todayRule, {backgroundColor: theme.colors.outline}]}
      />
    </View>
  );
}

function EmptyTimeline({onDiscover}: {onDiscover: () => void}) {
  const theme = useTheme();
  const c = theme.colors;
  return (
    <View
      testID="favorites.empty"
      style={[
        styles.empty,
        {borderColor: c.outline, borderRadius: theme.radius.card},
      ]}
    >
      <View style={[styles.emptyIcon, {backgroundColor: c.secondaryContainer}]}>
        <Icon name="heart" size={24} color={c.secondary} />
      </View>
      <Text variant="displayM">{strings.drawer.emptyTitle}</Text>
      <Text variant="body" tone="muted">
        {strings.drawer.emptyText}
      </Text>
      <Button
        label={strings.drawer.discover}
        onPress={onDiscover}
        testID="favorites.discover"
        style={styles.emptyButton}
      />
    </View>
  );
}

const styles = StyleSheet.create({
  section: {gap: 12},
  skeletonRow: {gap: 6, marginTop: 8},
  pastToggle: {
    alignSelf: 'flex-start',
    borderRadius: 999,
    paddingHorizontal: 16,
    paddingVertical: 10,
    minHeight: 44,
    justifyContent: 'center',
  },
  timeline: {marginTop: 8, gap: 20},
  line: {
    position: 'absolute',
    left: LINE_X - 1,
    top: 6,
    bottom: 0,
    width: 2,
    borderRadius: 1,
  },
  month: {gap: 14},
  monthTitle: {marginLeft: INDENT, fontSize: 14, lineHeight: 18},
  entry: {flexDirection: 'row', alignItems: 'flex-start', minHeight: 44},
  dot: {
    width: 10,
    height: 10,
    borderRadius: 5,
    borderWidth: 2,
    marginTop: 4,
    marginRight: INDENT - 10,
  },
  runningDot: {
    width: 14,
    height: 14,
    borderRadius: 7,
    marginLeft: LINE_X - 7,
    marginRight: INDENT - (LINE_X + 7),
    marginTop: 18,
    shadowOpacity: 0.8,
    shadowRadius: 8,
    shadowOffset: {width: 0, height: 0},
    elevation: 6,
  },
  runningCard: {flex: 1, borderWidth: 1, padding: 14, gap: 2},
  entryText: {flex: 1, gap: 2},
  name: {marginVertical: 2},
  today: {flexDirection: 'row', alignItems: 'center', gap: 10},
  todayDash: {width: 14, height: 2, borderRadius: 1},
  todayRule: {flex: 1, height: 1},
  empty: {
    borderWidth: 1.5,
    borderStyle: 'dashed',
    padding: 20,
    gap: 12,
    marginTop: 8,
  },
  emptyIcon: {
    width: 52,
    height: 52,
    borderRadius: 26,
    alignItems: 'center',
    justifyContent: 'center',
  },
  emptyButton: {alignSelf: 'flex-start'},
});
