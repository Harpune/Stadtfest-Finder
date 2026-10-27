/**
 * Optional filters of the AI search (R10c) in an accordion below the postal code: period,
 * categories, radius and fixed search focuses. There is no free text on purpose (privacy:
 * nothing a moderator types reaches the LLM or the web search).
 */
import React from 'react';
import {StyleSheet, View} from 'react-native';

import type {components} from '@/api/generated/schema';
import {Accordion, Button, Chip, DateField, Text} from '@/components';
import {useCategories} from '@/features/discover/useDiscoverData';
import {daysBetween, todayInBerlin} from '@/features/events/dates';
import {strings} from '@/strings/de';

export type AiSearchFocus = components['schemas']['AiSearchFocus'];
type RequestFilters = components['schemas']['AiSearchFilters'];

export interface AiFilterState {
  dateFrom: string | null;
  dateTo: string | null;
  categoryIds: string[];
  radiusKm: number | null;
  focus: AiSearchFocus[];
}

export const EMPTY_FILTERS: AiFilterState = {
  dateFrom: null,
  dateTo: null,
  categoryIds: [],
  radiusKm: null,
  focus: [],
};

/** Same limit as the backend: at most 365 days ahead. */
const HORIZON_DAYS = 365;
export const RADIUS_OPTIONS = [10, 25, 50] as const;
export const FOCUS_OPTIONS: readonly AiSearchFocus[] = [
  'village_festivals',
  'major_events',
  'municipal_calendars',
  'regional_press',
];
/** These two contradict each other; picking one drops the other. */
const EXCLUSIVE: Partial<Record<AiSearchFocus, AiSearchFocus>> = {
  village_festivals: 'major_events',
  major_events: 'village_festivals',
};

const t = strings.mod.ai.filters;

/** Number of filter groups in use (period counts once). */
export function activeFilterCount(state: AiFilterState): number {
  return [
    state.dateFrom !== null || state.dateTo !== null,
    state.categoryIds.length > 0,
    state.radiusKm !== null,
    state.focus.length > 0,
  ].filter(Boolean).length;
}

/** Problem with the period, checked like the backend; null if fine. */
export function periodError(
  state: AiFilterState,
  today: string = todayInBerlin(),
): string | null {
  if (state.dateFrom !== null && state.dateFrom < today) return t.periodPast;
  if (state.dateTo !== null) {
    if (state.dateTo < (state.dateFrom ?? today)) return t.periodOrder;
    if (daysBetween(today, state.dateTo) > HORIZON_DAYS) return t.periodTooFar;
  }
  return null;
}

/** Request body part; undefined without filters, so the request stays as before. */
export function toRequestFilters(
  state: AiFilterState,
): RequestFilters | undefined {
  if (activeFilterCount(state) === 0) return undefined;
  return {
    ...(state.dateFrom ? {dateFrom: state.dateFrom} : {}),
    ...(state.dateTo ? {dateTo: state.dateTo} : {}),
    ...(state.categoryIds.length ? {categoryIds: state.categoryIds} : {}),
    ...(state.radiusKm !== null ? {radiusKm: state.radiusKm} : {}),
    ...(state.focus.length ? {focus: state.focus} : {}),
  };
}

function toggle<T>(list: readonly T[], value: T): T[] {
  return list.includes(value)
    ? list.filter(item => item !== value)
    : [...list, value];
}

export function AiSearchFilters({
  value,
  onChange,
  expanded,
  onToggle,
}: {
  value: AiFilterState;
  onChange: (value: AiFilterState) => void;
  expanded: boolean;
  onToggle: () => void;
}) {
  const categories = useCategories();
  const count = activeFilterCount(value);
  const error = periodError(value);
  const today = todayInBerlin();

  const toggleFocus = (focus: AiSearchFocus) => {
    const adding = !value.focus.includes(focus);
    const other = EXCLUSIVE[focus];
    const next = toggle(value.focus, focus).filter(
      item => !(adding && item === other),
    );
    onChange({...value, focus: next});
  };

  return (
    <Accordion
      title={t.title}
      summary={count ? t.summaryActive(count) : t.summaryDefault}
      expanded={expanded}
      onToggle={onToggle}
      accent="mod"
      testID="mod.ai.filters"
    >
      <View style={styles.group}>
        <Text variant="caption" tone="muted">
          {t.period}
        </Text>
        <View style={styles.dates}>
          <View style={styles.date}>
            <DateField
              label={t.from}
              value={value.dateFrom}
              onChange={dateFrom => onChange({...value, dateFrom})}
              placeholder={t.datePlaceholder}
              minimumDate={today}
              invalid={error !== null && error !== t.periodTooFar}
              testID="mod.ai.filters.dateFrom"
            />
          </View>
          <View style={styles.date}>
            <DateField
              label={t.to}
              value={value.dateTo}
              onChange={dateTo => onChange({...value, dateTo})}
              placeholder={t.datePlaceholder}
              minimumDate={value.dateFrom ?? today}
              invalid={error !== null && error !== t.periodPast}
              testID="mod.ai.filters.dateTo"
            />
          </View>
        </View>
        {error ? (
          <Text
            variant="caption"
            tone="error"
            testID="mod.ai.filters.periodError"
          >
            {error}
          </Text>
        ) : null}
      </View>

      {categories.data?.length ? (
        <View style={styles.group}>
          <Text variant="caption" tone="muted">
            {t.categories}
          </Text>
          <View style={styles.chips}>
            {categories.data.map(category => (
              <Chip
                key={category.id}
                label={category.name}
                emoji={category.emoji}
                active={value.categoryIds.includes(category.id)}
                onPress={() =>
                  onChange({
                    ...value,
                    categoryIds: toggle(value.categoryIds, category.id),
                  })
                }
                variant="sheet"
                accent="mod"
                testID={`mod.ai.filters.category.${category.id}`}
              />
            ))}
          </View>
        </View>
      ) : null}

      <View style={styles.group}>
        <Text variant="caption" tone="muted">
          {t.radius}
        </Text>
        <View style={styles.chips}>
          {RADIUS_OPTIONS.map(km => (
            <Chip
              key={km}
              label={t.radiusKm(km)}
              active={value.radiusKm === km}
              onPress={() =>
                onChange({
                  ...value,
                  radiusKm: value.radiusKm === km ? null : km,
                })
              }
              variant="sheet"
              accent="mod"
              testID={`mod.ai.filters.radius.${km}`}
            />
          ))}
        </View>
      </View>

      <View style={styles.group}>
        <Text variant="caption" tone="muted">
          {t.focus}
        </Text>
        <View style={styles.chips}>
          {FOCUS_OPTIONS.map(focus => (
            <Chip
              key={focus}
              label={t.focusOptions[focus]}
              active={value.focus.includes(focus)}
              onPress={() => toggleFocus(focus)}
              variant="sheet"
              accent="mod"
              testID={`mod.ai.filters.focus.${focus}`}
            />
          ))}
        </View>
      </View>

      {count ? (
        <Button
          label={t.reset}
          variant="ghost"
          onPress={() => onChange(EMPTY_FILTERS)}
          testID="mod.ai.filters.reset"
        />
      ) : null}
    </Accordion>
  );
}

const styles = StyleSheet.create({
  group: {gap: 8},
  dates: {flexDirection: 'row', gap: 12},
  date: {flex: 1},
  chips: {flexDirection: 'row', flexWrap: 'wrap', gap: 8},
});
