/**
 * Event detail (R04, screens 02-01 to 02-05): gallery, header, info block, description,
 * program, place with mini map, directions, website and a fixed footer with route/invite.
 */
import {router} from 'expo-router';
import * as WebBrowser from 'expo-web-browser';
import React from 'react';
import {
  Linking,
  Platform,
  ScrollView,
  Share,
  StyleSheet,
  View,
} from 'react-native';
import {useSafeAreaInsets} from 'react-native-safe-area-context';

import {
  Button,
  CategoryPill,
  ComingAlongHint,
  EmptyState,
  FavoriteButton,
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
import {comingAlongText, personAvatar} from '../invitations/format';
import {navigate} from '../navigation/navigate';
import {buildCategoryLookup} from '../discover/categoryLookup';
import {offlineStyle} from '../discover/mapStyle';
import {useCategories} from '../discover/useDiscoverData';
import {roundedDistanceKm} from '../discover/geo';
import {useTileStyle} from '../discover/useTileStyle';
import {
  formatDateRange,
  formatDateRangeLong,
  formatProgramDate,
  todayInBerlin,
} from '../events/dates';
import {eventStatus} from '../events/status';
import {useDevicePosition} from '../events/useDevicePosition';
import {
  favoriteEntryFrom,
  useFavoriteIds,
  useToggleFavorite,
} from '../favorites/useFavorites';
import {displayHost, eventShareUrl, mapsRouteUrl, safeWebUrl} from './links';
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
  const position = useDevicePosition();
  const today = todayInBerlin();
  const favoriteIds = useFavoriteIds();
  const toggleFavorite = useToggleFavorite();

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
  // Inviting is not possible to cancelled or past events (R14-US1).
  const invitable = !!base && !cancelled && base.endDate >= today;
  const comingAlong = detail?.invitationSummary;
  // Distance only with location access, computed on the device (no position is sent).
  const distanceKm =
    position && base ? roundedDistanceKm(position, base) : undefined;
  const websiteUrl = safeWebUrl(detail?.websiteUrl);
  const isFavorite = favoriteIds.has(eventId);

  // Guests get the hint; signed-in users toggle optimistically (R06-US1).
  const onFavoritePress = () => {
    if (!requestAccountAction({type: 'favorite', eventId})) return;
    if (!base || !category) return;
    const event = {
      id: eventId,
      name: base.name,
      shortName: base.shortName,
      status: base.status,
      startDate: base.startDate,
      endDate: base.endDate,
      place: base.place,
      city: base.city,
      lat: base.lat,
      lon: base.lon,
      categoryId: detail?.category.id ?? summary?.categoryId ?? '',
    };
    void toggleFavorite(favoriteEntryFrom(event, category), !isFavorite);
  };

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

  // Sharing works without an account: native share sheet with name, period and link.
  const shareEvent = async () => {
    const url = eventShareUrl(eventId);
    const message = base
      ? strings.detail.shareMessage(
          base.name,
          formatDateRange(base.startDate, base.endDate),
          url,
        )
      : url;
    try {
      await Share.share(
        Platform.OS === 'ios' ? {message, url} : {message, title: base?.name},
      );
    } catch {
      // The user closed the sheet or no share target exists; nothing to report.
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

  const addressLine = detail ? formatAddress(detail) : '';

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

          {comingAlong && comingAlong.people.length > 0 ? (
            <ComingAlongHint
              people={comingAlong.people.map(p => personAvatar(p, c))}
              text={comingAlongText(comingAlong.people)}
              onPress={() =>
                comingAlong.role === 'host'
                  ? navigate({
                      pathname: '/einladen/[eventId]',
                      params: {eventId},
                    })
                  : navigate({
                      pathname: '/einladung/[id]',
                      params: {id: comingAlong.invitationId},
                    })
              }
              testID="detail.comingAlong"
            />
          ) : null}

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
            onPress={() => void shareEvent()}
            testID="detail.share"
          />
          <FavoriteButton
            active={isFavorite}
            accessibilityLabel={
              isFavorite
                ? strings.favorites.remove(base?.name ?? '')
                : strings.detail.favorite
            }
            onPress={onFavoritePress}
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
          disabled={!invitable}
          onPress={() => {
            if (!requestAccountAction({type: 'invite', eventId})) return;
            navigate({pathname: '/einladen/[eventId]', params: {eventId}});
          }}
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

/**
 * "Place, street, ZIP city" without empty or repeated parts: an address that is only the
 * city, or a part that another part already lists (e.g. "Marktplatz 1" next to
 * "Marktplatz 1, 73430 Aalen"), is left out. A pin may have coordinates as address.
 */
export function formatAddress(detail: {
  place: string;
  address: string;
  postalCode: string;
  city: string;
}): string {
  const locality = `${detail.postalCode} ${detail.city}`.trim();
  const sameAsLocality = [detail.city, detail.postalCode, locality].map(v =>
    v.trim().toLowerCase(),
  );
  const address = sameAsLocality.includes(detail.address.trim().toLowerCase())
    ? ''
    : detail.address;
  const parts = [detail.place, address, locality]
    .map(part => part.trim())
    .filter(part => part);
  const segments = parts.map(part =>
    part
      .toLowerCase()
      .split(',')
      .map(segment => segment.trim()),
  );
  const redundant = (i: number) =>
    segments.some(
      (other, j) =>
        j !== i &&
        other.includes(parts[i]?.toLowerCase() ?? '') &&
        (other.length > 1 || j < i),
    );
  return parts.filter((_, i) => !redundant(i)).join(', ');
}
