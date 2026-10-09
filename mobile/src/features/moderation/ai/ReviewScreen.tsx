/**
 * Review the finds of one AI search (R10-US4, 09-04/09-05): one find at a time with its
 * source; publish, edit or discard; a summary at the end. ✕ pauses, drafts stay.
 */
import {useQuery, useQueryClient} from '@tanstack/react-query';
import {router, useFocusEffect} from 'expo-router';
import * as WebBrowser from 'expo-web-browser';
import React, {useCallback, useMemo, useRef, useState} from 'react';
import {Pressable, ScrollView, StyleSheet, View} from 'react-native';

import {navigate} from '@/features/navigation/navigate';
import {fetchClient} from '@/api/client';
import {
  Button,
  EventImage,
  Icon,
  IconButton,
  Skeleton,
  Text,
  useToast,
} from '@/components';
import {useCategories} from '@/features/discover/useDiscoverData';
import {formatDateRange} from '@/features/events/dates';
import {strings} from '@/strings/de';
import {useTheme} from '@/theme';

import {formFromEvent, ModEventDetail, publishErrors} from '../form';
import {MOD_EVENTS_QUERY, modApi, useModEvent} from '../useModeration';
import {useAiSearch} from './AiSearchProvider';

type Outcome = 'published' | 'edited' | 'discarded';

function domainOf(url: string): string {
  return url.replace(/^https?:\/\/(www\.)?/i, '').replace(/[?#].*$/, '');
}

function useJob(jobId: string) {
  return useQuery({
    queryKey: ['get', '/v1/mod/ai-searches/{jobId}', jobId] as const,
    queryFn: async () => {
      const {data, error} = await fetchClient.GET(
        '/v1/mod/ai-searches/{jobId}',
        {
          params: {path: {jobId}},
        },
      );
      if (error) throw new Error(error.error);
      return data;
    },
  });
}

/** Finds already handled elsewhere (published, deleted) count as done when opening. */
function useInitialOutcomes(ids: readonly string[]) {
  return useQuery({
    queryKey: ['get', '/v1/mod/events', {ids: ids.join(',')}] as const,
    enabled: ids.length > 0,
    queryFn: async () => {
      const {data} = await fetchClient.GET('/v1/mod/events', {
        params: {query: {ids: [...ids]}},
        // The API expects `ids=a,b` (OpenAPI `explode: false`).
        querySerializer: {array: {style: 'form', explode: false}},
      });
      const byId = new Map((data?.items ?? []).map(item => [item.id, item]));
      const outcomes: Record<string, Outcome> = {};
      for (const id of ids) {
        const item = byId.get(id);
        if (!item) outcomes[id] = 'discarded';
        else if (item.status !== 'draft') outcomes[id] = 'published';
      }
      return outcomes;
    },
  });
}

export function ReviewScreen({jobId}: {jobId: string}) {
  const theme = useTheme();
  const c = theme.colors;
  const toast = useToast();
  const queryClient = useQueryClient();
  const ai = useAiSearch();
  const job = useJob(jobId);
  const ids = useMemo(() => job.data?.newEventIds ?? [], [job.data]);
  const initial = useInitialOutcomes(ids);
  const [outcomes, setOutcomes] = useState<Record<string, Outcome>>({});
  const all = useMemo(
    () => ({...(initial.data ?? {}), ...outcomes}),
    [initial.data, outcomes],
  );
  const currentId = ids.find(id => !all[id]) ?? null;
  const index = currentId ? ids.indexOf(currentId) : ids.length;
  const detail = useModEvent(currentId);
  const [busy, setBusy] = useState<'publish' | 'discard' | null>(null);
  // The find opened in the form: on return, decide by its stored state.
  const editing = useRef<{id: string; version: number} | null>(null);

  const mark = (id: string, outcome: Outcome) =>
    setOutcomes(current => ({...current, [id]: outcome}));

  const refreshOverview = () =>
    void queryClient.invalidateQueries({queryKey: MOD_EVENTS_QUERY.queryKey});

  useFocusEffect(
    useCallback(() => {
      const opened = editing.current;
      if (!opened) return;
      editing.current = null;
      void fetchClient
        .GET('/v1/mod/events/{eventId}', {params: {path: {eventId: opened.id}}})
        .then(({data, response}) => {
          if (response.status === 404) mark(opened.id, 'discarded');
          else if (data && data.status !== 'draft')
            mark(opened.id, 'published');
          else if (data && data.version > opened.version)
            mark(opened.id, 'edited');
        })
        .catch(() => undefined);
    }, []),
  );

  const openForm = (event: ModEventDetail) => {
    editing.current = {id: event.id, version: event.version};
    navigate(`/mod/fest/${event.id}`);
  };

  const categories = useCategories();
  const activeIds = useMemo(
    () => new Set((categories.data ?? []).map(category => category.id)),
    [categories.data],
  );

  const publish = async (event: ModEventDetail) => {
    if (
      Object.keys(publishErrors(formFromEvent(event), activeIds)).length > 0
    ) {
      toast(strings.mod.ai.needsFields);
      openForm(event);
      return;
    }
    setBusy('publish');
    const result = await modApi.publish(event.id);
    setBusy(null);
    if (!result.ok) {
      if (result.status === 422) {
        toast(strings.mod.ai.needsFields);
        openForm(event);
      } else {
        toast(strings.mod.toast.failed);
      }
      return;
    }
    toast(strings.mod.ai.published);
    refreshOverview();
    mark(event.id, 'published');
  };

  const discard = async (event: ModEventDetail) => {
    setBusy('discard');
    const result = await modApi.remove(event.id);
    setBusy(null);
    if (!result.ok && result.status !== 404) {
      toast(strings.mod.toast.failed);
      return;
    }
    toast(strings.mod.ai.discarded);
    refreshOverview();
    mark(event.id, 'discarded');
  };

  const pause = () => {
    toast(strings.mod.ai.paused);
    if (router.canGoBack()) router.back();
    else router.replace('/mod');
  };

  const finish = () => {
    ai.dismiss();
    if (router.canGoBack()) router.back();
    else router.replace('/mod');
  };

  const done = ids.length > 0 && currentId === null;
  const counts = Object.values(all).reduce(
    (total, outcome) => ({...total, [outcome]: total[outcome] + 1}),
    {published: 0, edited: 0, discarded: 0} as Record<Outcome, number>,
  );

  return (
    <View
      style={[styles.root, {backgroundColor: c.background}]}
      testID="mod.review"
    >
      <View style={styles.header}>
        <IconButton
          icon={<Icon name="close" size={24} />}
          accessibilityLabel={strings.mod.ai.close}
          onPress={done ? finish : pause}
          variant="surface"
          testID="mod.review.close"
        />
        <View style={styles.headerText}>
          <Text variant="displayM" accessibilityRole="header">
            {strings.mod.ai.reviewTitle}
          </Text>
          <Text variant="meta" tone="muted" testID="mod.review.progress">
            {done
              ? strings.mod.ai.reviewDone(ids.length)
              : ids.length > 0
                ? strings.mod.ai.reviewProgress(index + 1, ids.length)
                : ''}
          </Text>
        </View>
      </View>
      <View style={styles.segments} testID="mod.review.segments">
        {ids.map(id => (
          <View
            key={id}
            style={[
              styles.segment,
              {
                backgroundColor:
                  all[id] === 'discarded'
                    ? c.secondary
                    : all[id]
                      ? c.mod.primary
                      : c.outline,
              },
            ]}
          />
        ))}
      </View>

      {done ? (
        <Summary counts={counts} onDone={finish} />
      ) : !detail.data || job.isPending || initial.isPending ? (
        <View style={styles.content} testID="mod.review.loading">
          <Skeleton width="100%" height={180} />
          <Skeleton width="70%" height={32} />
          <Skeleton width="100%" height={90} />
        </View>
      ) : (
        <Find
          event={detail.data}
          postalCode={job.data?.postalCode ?? ''}
          categoryName={
            categories.data?.find(item => item.id === detail.data?.categoryId)
              ?.name
          }
          categoryEmoji={
            categories.data?.find(item => item.id === detail.data?.categoryId)
              ?.emoji
          }
          busy={busy}
          onPublish={event => void publish(event)}
          onEdit={openForm}
          onDiscard={event => void discard(event)}
        />
      )}
    </View>
  );
}

function Find({
  event,
  postalCode,
  categoryName,
  categoryEmoji,
  busy,
  onPublish,
  onEdit,
  onDiscard,
}: {
  event: ModEventDetail;
  postalCode: string;
  categoryName?: string;
  categoryEmoji?: string;
  busy: 'publish' | 'discard' | null;
  onPublish: (event: ModEventDetail) => void;
  onEdit: (event: ModEventDetail) => void;
  onDiscard: (event: ModEventDetail) => void;
}) {
  const theme = useTheme();
  const c = theme.colors;
  const period =
    event.startDate && event.endDate
      ? `${formatDateRange(event.startDate, event.endDate)} ${event.endDate.slice(0, 4)}`
      : null;
  const location = [
    // The LLM often names the street as the place ("Karlstraße", "Karlstraße 26, …").
    event.address?.startsWith(event.place ?? '') ? '' : event.place,
    event.address,
  ]
    .filter(Boolean)
    .join(', ');
  const headline = [period, location].filter(Boolean).join(' · ');
  const cover = event.images[0]?.image?.cardUrl ?? event.images[0]?.image?.url;
  const rows: {label: string; value: string | null; required?: boolean}[] = [
    {
      label: strings.mod.ai.fields.category,
      value: categoryName ?? null,
      required: true,
    },
    {label: strings.mod.ai.fields.period, value: period, required: true},
    {
      label: strings.mod.ai.fields.location,
      value: location || null,
      required: true,
    },
    {
      label: strings.mod.ai.fields.openingHours,
      value: event.openingHours.join('\n') || null,
    },
    {label: strings.mod.ai.fields.price, value: event.price ?? null},
    {
      label: strings.mod.ai.fields.description,
      value: event.description ?? null,
    },
  ];
  return (
    <>
      <ScrollView
        contentContainerStyle={styles.content}
        testID="mod.review.find"
      >
        <EventImage
          uri={cover}
          label={strings.mod.ai.noImage}
          style={styles.image}
          radius={theme.radius.block}
        />
        <View style={styles.pills}>
          <View style={[styles.pill, {backgroundColor: c.mod.container}]}>
            <Text
              variant="meta"
              tone="mod"
              style={{fontFamily: theme.fonts.semibold}}
            >
              {strings.mod.ai.autoFound}
            </Text>
          </View>
          {categoryName ? (
            <View style={[styles.pill, {backgroundColor: c.surfaceVariant}]}>
              <Text variant="meta">{`${categoryEmoji ?? ''} ${categoryName}`}</Text>
            </View>
          ) : null}
        </View>
        <Text variant="displayL" testID="mod.review.name">
          {event.name}
        </Text>
        {headline ? (
          <Text variant="body" tone="muted">
            {headline}
          </Text>
        ) : null}
        {event.sourceUrl ? (
          <Pressable
            accessibilityRole="link"
            onPress={() =>
              void WebBrowser.openBrowserAsync(event.sourceUrl ?? '')
            }
            style={[
              styles.source,
              {borderColor: c.outline, borderRadius: theme.radius.block},
            ]}
            testID="mod.review.source"
          >
            <Icon name="globe" size={22} />
            <View style={styles.sourceText}>
              <Text variant="meta" tone="muted">
                {strings.mod.ai.foundOn}
              </Text>
              <Text variant="bodyStrong" tone="mod" numberOfLines={1}>
                {domainOf(event.sourceUrl)}
              </Text>
              <Text variant="meta" tone="muted">
                {strings.mod.ai.searchFor(postalCode, strings.mod.ai.today)}
              </Text>
            </View>
            <Text variant="bodyStrong" tone="mod">
              {strings.mod.ai.open}
            </Text>
          </Pressable>
        ) : null}
        <View
          style={[
            styles.table,
            {backgroundColor: c.surface, borderRadius: theme.radius.block},
          ]}
        >
          {rows.map((row, i) => (
            <View
              key={row.label}
              style={[
                styles.row,
                i > 0 && {
                  borderTopWidth: StyleSheet.hairlineWidth,
                  borderTopColor: c.outline,
                },
              ]}
            >
              <Text variant="body" tone="muted" style={styles.rowLabel}>
                {row.label}
              </Text>
              <Text
                variant="body"
                tone={
                  row.value ? 'default' : row.required ? 'secondary' : 'muted'
                }
                style={styles.rowValue}
                testID={`mod.review.field.${i}`}
              >
                {row.value ?? (row.required ? strings.mod.ai.missing : '–')}
              </Text>
            </View>
          ))}
        </View>
      </ScrollView>
      {/* Three labels in one row break mid-word on a 393 dp screen ("Verwerfe|n"),
          so the main action gets its own row. */}
      <View style={[styles.footerStack, {borderTopColor: c.outline}]}>
        <Button
          label={strings.mod.ai.publish}
          variant="mod"
          onPress={() => onPublish(event)}
          loading={busy === 'publish'}
          disabled={busy !== null && busy !== 'publish'}
          testID="mod.review.publish"
        />
        <View style={styles.footerRow}>
          <Button
            label={strings.mod.ai.discard}
            variant="danger"
            onPress={() => onDiscard(event)}
            loading={busy === 'discard'}
            disabled={busy !== null && busy !== 'discard'}
            style={styles.footerSmall}
            testID="mod.review.discard"
          />
          <Button
            label={strings.mod.ai.edit}
            variant="secondary"
            onPress={() => onEdit(event)}
            disabled={busy !== null}
            style={styles.footerSmall}
            testID="mod.review.edit"
          />
        </View>
      </View>
    </>
  );
}

function Summary({
  counts,
  onDone,
}: {
  counts: Record<Outcome, number>;
  onDone: () => void;
}) {
  const theme = useTheme();
  const c = theme.colors;
  return (
    <>
      <View style={styles.summary} testID="mod.review.summary">
        <View style={[styles.check, {backgroundColor: c.mod.container}]}>
          <Icon name="check" size={40} color={c.mod.primary} strokeWidth={3} />
        </View>
        <Text variant="displayL" accessibilityRole="header">
          {strings.mod.ai.allDone}
        </Text>
        <View style={styles.summaryLines}>
          <Text variant="body" tone="muted">
            {strings.mod.ai.summaryPublished(counts.published)}
          </Text>
          <Text variant="body" tone="muted">
            {strings.mod.ai.summaryEdited(counts.edited)}
          </Text>
          <Text variant="body" tone="muted">
            {strings.mod.ai.summaryDiscarded(counts.discarded)}
          </Text>
        </View>
      </View>
      <View style={[styles.footer, {borderTopColor: c.outline}]}>
        <Button
          label={strings.mod.ai.toOverview}
          variant="mod"
          onPress={onDone}
          style={styles.footerLarge}
          testID="mod.review.done"
        />
      </View>
    </>
  );
}

const styles = StyleSheet.create({
  root: {flex: 1},
  header: {
    flexDirection: 'row',
    alignItems: 'center',
    gap: 12,
    paddingHorizontal: 16,
    paddingTop: 10,
  },
  headerText: {flex: 1},
  segments: {
    flexDirection: 'row',
    gap: 6,
    paddingHorizontal: 16,
    paddingVertical: 12,
  },
  segment: {flex: 1, height: 4, borderRadius: 2},
  content: {padding: 16, gap: 14, paddingBottom: 32},
  image: {height: 160},
  pills: {flexDirection: 'row', flexWrap: 'wrap', gap: 8},
  pill: {paddingHorizontal: 12, paddingVertical: 6, borderRadius: 10},
  source: {
    flexDirection: 'row',
    alignItems: 'center',
    gap: 12,
    padding: 14,
    borderWidth: 1,
  },
  sourceText: {flex: 1, gap: 2},
  table: {paddingHorizontal: 14},
  row: {flexDirection: 'row', gap: 12, paddingVertical: 12},
  rowLabel: {width: 120},
  rowValue: {flex: 1},
  footer: {flexDirection: 'row', gap: 8, padding: 12, borderTopWidth: 1},
  footerStack: {gap: 8, padding: 12, borderTopWidth: 1},
  footerRow: {flexDirection: 'row', gap: 8},
  footerSmall: {flex: 1},
  footerLarge: {flex: 1.6},
  summary: {
    flex: 1,
    alignItems: 'center',
    justifyContent: 'center',
    gap: 16,
    padding: 24,
  },
  check: {
    width: 88,
    height: 88,
    borderRadius: 44,
    alignItems: 'center',
    justifyContent: 'center',
  },
  summaryLines: {alignItems: 'center', gap: 6},
});
