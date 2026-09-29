/**
 * Event detail (R04, screens 02-01 to 02-05): gallery, header, info block, description,
 * program, place with mini map, directions, website and a fixed footer with route/invite.
 */
import {router} from 'expo-router';
import * as WebBrowser from 'expo-web-browser';
import React from 'react';
import {Linking, Platform, ScrollView, StyleSheet, View} from 'react-native';
import {useSafeAreaInsets} from 'react-native-safe-area-context';

import {
  Button,
  CategoryPill,
  EmptyState,
  Gallery,
  Icon,
  IconButton,
  InfoBlock,
  InfoRow,
  LinkRow,
  MiniMap,
  ProgramList,
  SectionHeader,
  Skeleton,
  StatusPill,
  StickyFooter,
  Text,
  useToast,
} from '@/components';
import {strings} from '@/strings/de';
import {useTheme} from '@/theme';

import {useAuth} from '../auth/AuthProvider';
import {buildCategoryLookup} from '../discover/categoryLookup';
import {offlineStyle} from '../discover/mapStyle';
import {useCategories} from '../discover/useDiscoverData';
import {useTileStyle} from '../discover/useTileStyle';
import {
  formatDateRangeLong,
  formatProgramDate,
  todayInBerlin,
} from '../events/dates';
import {eventStatus} from '../events/status';
import {displayHost, mapsRouteUrl, safeWebUrl} from './links';
import {useEventDetail} from './useEventDetail';

const CONTENT_OVERLAP = 28;
const FOOTER_SPACE = 110;

function goBackOrHome() {
  if (router.canGoBack()) router.back();
  else router.replace('/');
}

export function EventDetailScreen({eventId}: {eventId: string}) {
  const theme = useTheme();
  const c = theme.colors;
  const insets = useSafeAreaInsets();
  const toast = useToast();
  const {requestAccountAction} = useAuth();
  const {summary, detail, notFound, isLoading, isError, refetch} =
    useEventDetail(eventId);
  const categories = useCategories();
  const tileStyle = useTileStyle(theme.scheme);
  const today = todayInBerlin();

  if (notFound) {
    return (
      <View
        style={[styles.centered, {backgroundColor: c.background}]}
        testID="detail.notFound"
      >
        <EmptyState
          testID="detail.notFound.card"
          title={strings.detail.notFoundTitle}
          text={strings.detail.notFoundText}
          primary={{
            label: strings.detail.backToMap,
            onPress: goBackOrHome,
            testID: 'detail.toMap',
          }}
        />
      </View>
    );
  }

  // Header data: full detail, else the cached list entry (shown immediately).
  const base = detail ?? summary;
  const categoryOf = buildCategoryLookup(categories.data);
  const category =
    detail?.category ?? (summary ? categoryOf(summary.categoryId) : undefined);
  const status = base ? eventStatus(base, today) : undefined;
  const cancelled = base?.status === 'cancelled';
  const distanceKm = detail?.distanceKm ?? summary?.distanceKm;
  const websiteUrl = safeWebUrl(detail?.websiteUrl);

  const openRoute = async () => {
    if (!base) return;
    const url = mapsRouteUrl(Platform.OS === 'ios' ? 'ios' : 'android', {
      lat: base.lat,
      lon: base.lon,
      name: base.name,
    });
    try {
      await Linking.openURL(url);
    } catch {
      toast(strings.detail.mapsUnavailable);
    }
  };

  const infoRows: InfoRow[] = base
    ? [
        {
          icon: 'calendar',
          label: strings.detail.period,
          lines: [formatDateRangeLong(base.startDate, base.endDate)],
        },
        ...(detail && detail.openingHours.length > 0
          ? [
              {
                icon: 'clock' as const,
                label: strings.detail.openingHours,
                lines: detail.openingHours,
              },
            ]
          : []),
        ...(detail?.price
          ? [
              {
                icon: 'ticket' as const,
                label: strings.detail.price,
                lines: [detail.price],
              },
            ]
          : []),
      ]
    : [];

  const addressLine = detail
    ? [
        detail.place !== detail.address ? detail.place : null,
        detail.address,
        `${detail.postalCode} ${detail.city}`,
      ]
        .filter(part => part)
        .join(', ')
    : '';

  return (
    <View
      style={[styles.root, {backgroundColor: c.background}]}
      testID="detail.screen"
    >
      <ScrollView
        contentContainerStyle={{paddingBottom: FOOTER_SPACE + insets.bottom}}
        showsVerticalScrollIndicator={false}
      >
        <Gallery
          images={detail?.images ?? []}
          name={base?.name ?? ''}
          testID="detail.gallery"
        />
        <View
          style={[
            styles.content,
            {
              backgroundColor: c.background,
              borderTopLeftRadius: theme.radius.sheet,
              borderTopRightRadius: theme.radius.sheet,
            },
          ]}
        >
          {base && status ? (
            <View style={styles.header}>
              <View style={styles.pills}>
                {category ? (
                  <CategoryPill emoji={category.emoji} name={category.name} />
                ) : null}
                <StatusPill
                  label={status.label}
                  tone={status.tone}
                  testID="detail.status"
                />
              </View>
              <Text variant="displayXL" testID="detail.title">
                {base.name}
              </Text>
              <Text variant="body" tone="muted">
                {base.place}, {base.city}
                {typeof distanceKm === 'number'
                  ? ` · ${strings.detail.distanceAway(strings.discover.distance(distanceKm))}`
                  : ''}
              </Text>
              {cancelled && detail?.cancelReason ? (
                <Text
                  variant="body"
                  tone="secondary"
                  testID="detail.cancelReason"
                >
                  {strings.detail.cancelReason(detail.cancelReason)}
                </Text>
              ) : null}
            </View>
          ) : (
            <View style={styles.header}>
              <Skeleton width={180} height={30} />
              <Skeleton width={260} height={36} />
              <Skeleton width={200} height={16} />
            </View>
          )}

          {base ? (
            <InfoBlock rows={infoRows} loading={!detail} testID="detail.info" />
          ) : null}

          {isError && !detail ? (
            <EmptyState
              testID="detail.error"
              title={strings.detail.loadFailed}
              text=""
              primary={{
                label: strings.common.retry,
                onPress: () => void refetch(),
                testID: 'detail.retry',
              }}
            />
          ) : null}

          {isLoading && !detail ? (
            <View style={styles.section} testID="detail.loading">
              <Skeleton width={180} height={24} />
              <Skeleton height={14} />
              <Skeleton height={14} />
              <Skeleton width={220} height={14} />
            </View>
          ) : null}

          {detail?.description ? (
            <View style={styles.section} testID="detail.about">
              <SectionHeader title={strings.detail.about} />
              <Text variant="body" tone="muted">
                {detail.description}
              </Text>
            </View>
          ) : null}

          {detail && detail.program.length > 0 ? (
            <View style={styles.section}>
              <SectionHeader title={strings.detail.program} />
              <ProgramList
                testID="detail.program"
                entries={detail.program.map((item, i) => {
                  const date = formatProgramDate(item.date);
                  return {
                    key: `${item.date}-${i}`,
                    weekday: date.weekday,
                    day: date.day,
                    title: item.title,
                    subtitle: [item.timeLabel, item.subtitle]
                      .filter(Boolean)
                      .join(' · '),
                  };
                })}
              />
            </View>
          ) : null}

          {detail ? (
            <View style={styles.section} testID="detail.place">
              <SectionHeader title={strings.detail.place} />
              <MiniMap
                testID="detail.miniMap"
                lat={detail.lat}
                lon={detail.lon}
                emoji={detail.category.emoji}
                mapStyle={tileStyle ?? offlineStyle(c.surface)}
                onPress={() => void openRoute()}
              />
              <Text variant="body">{addressLine}</Text>
            </View>
          ) : null}

          {detail && (detail.transit || detail.parking) ? (
            <View style={styles.section} testID="detail.directions">
              <SectionHeader title={strings.detail.directions} />
              {detail.transit ? (
                <DirectionRow
                  icon="train"
                  label={strings.detail.transit}
                  text={detail.transit}
                />
              ) : null}
              {detail.parking ? (
                <DirectionRow
                  icon="parking"
                  label={strings.detail.parking}
                  text={detail.parking}
                />
              ) : null}
            </View>
          ) : null}

          {websiteUrl ? (
            <LinkRow
              icon="globe"
              label={strings.detail.website}
              value={displayHost(websiteUrl)}
              onPress={() => void WebBrowser.openBrowserAsync(websiteUrl)}
              testID="detail.website"
            />
          ) : null}
        </View>
      </ScrollView>

      <View
        style={[styles.topBar, {top: insets.top + 8}]}
        pointerEvents="box-none"
      >
        <IconButton
          icon={<Icon name="chevronLeft" size={24} />}
          accessibilityLabel={strings.detail.back}
          onPress={goBackOrHome}
          testID="detail.back"
        />
        <View style={styles.topActions}>
          <IconButton
            icon={<Icon name="share" size={21} />}
            accessibilityLabel={strings.detail.share}
            onPress={() => requestAccountAction({type: 'share', eventId})}
            testID="detail.share"
          />
          <IconButton
            icon={<Icon name="heart" size={21} />}
            accessibilityLabel={strings.detail.favorite}
            onPress={() => requestAccountAction({type: 'favorite', eventId})}
            testID="detail.favorite"
          />
        </View>
      </View>

      <StickyFooter testID="detail.footer">
        <Button
          label={strings.detail.route}
          onPress={() => void openRoute()}
          disabled={!base}
          testID="detail.route"
          style={styles.route}
        />
        <Button
          label={strings.detail.invite}
          variant="secondary"
          disabled={cancelled || !base}
          onPress={() => requestAccountAction({type: 'invite', eventId})}
          testID="detail.invite"
        />
      </StickyFooter>
    </View>
  );
}

function DirectionRow({
  icon,
  label,
  text,
}: {
  icon: 'train' | 'parking';
  label: string;
  text: string;
}) {
  const theme = useTheme();
  return (
    <View style={styles.directionRow}>
      <Icon name={icon} size={22} color={theme.colors.secondaryText} />
      <Text variant="body" style={styles.directionText}>
        <Text variant="bodyStrong">{label} </Text>
        {text}
      </Text>
    </View>
  );
}

const styles = StyleSheet.create({
  root: {flex: 1},
  centered: {flex: 1, justifyContent: 'center', padding: 16},
  content: {
    marginTop: -CONTENT_OVERLAP,
    paddingHorizontal: 16,
    paddingTop: 22,
    gap: 22,
  },
  header: {gap: 10},
  pills: {flexDirection: 'row', flexWrap: 'wrap', gap: 8},
  section: {gap: 12},
  topBar: {
    position: 'absolute',
    left: 16,
    right: 16,
    flexDirection: 'row',
    justifyContent: 'space-between',
  },
  topActions: {flexDirection: 'row', gap: 10},
  route: {flex: 1},
  directionRow: {flexDirection: 'row', gap: 12, alignItems: 'flex-start'},
  directionText: {flex: 1},
});
