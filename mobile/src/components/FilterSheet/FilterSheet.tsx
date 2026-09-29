import React, {useEffect, useState} from 'react';
import {Pressable, StyleSheet, View} from 'react-native';

import {
  DEFAULT_FILTER,
  DiscoverFilter,
  MAX_RADIUS_KM,
  MIN_RADIUS_KM,
  RADIUS_STEP_KM,
  TimeKind,
  toggleValue,
} from '@/features/discover/filter';
import {strings} from '@/strings/de';

import {BottomSheet} from '../BottomSheet/BottomSheet';
import {Button} from '../Button/Button';
import {Chip} from '../Chip/Chip';
import {MonthGrid, MonthGridOption} from '../MonthGrid/MonthGrid';
import {RangeSlider} from '../RangeSlider/RangeSlider';
import {Text} from '../Text/Text';

export interface FilterSheetCategory {
  id: string;
  name: string;
  emoji: string;
}

export interface FilterSheetProps {
  visible: boolean;
  /** Applied filter; the sheet edits a copy (draft) of it. */
  filter: DiscoverFilter;
  categories: readonly FilterSheetCategory[];
  monthOptions: readonly MonthGridOption[];
  /** "vom Standort Aalen" or "vom Kartenmittelpunkt". */
  originCaption: string;
  /** Live count for the draft (`/v1/events/count`); undefined while unknown. */
  previewCount: number | undefined;
  previewLoading?: boolean;
  onDraftChange: (draft: DiscoverFilter) => void;
  onApply: (draft: DiscoverFilter) => void;
  onClose: () => void;
}

const TIME_OPTIONS: {kind: TimeKind; label: string}[] = [
  {kind: 'all', label: strings.filter.timeAll},
  {kind: 'today', label: strings.filter.timeToday},
  {kind: 'weekend', label: strings.filter.timeWeekend},
  {kind: 'months', label: strings.filter.timeMonths},
];

/** Filter sheet (screens 01-05/01-06): time, categories, distance; applied only on confirm. */
export function FilterSheet({
  visible,
  filter,
  categories,
  monthOptions,
  originCaption,
  previewCount,
  previewLoading = false,
  onDraftChange,
  onApply,
  onClose,
}: FilterSheetProps) {
  const [draft, setDraft] = useState(filter);

  // Every opening starts from a fresh copy of the applied filter; closing discards the draft.
  useEffect(() => {
    if (visible) setDraft(filter);
  }, [visible, filter]);

  useEffect(() => {
    if (visible) onDraftChange(draft);
  }, [visible, draft, onDraftChange]);

  const update = (patch: Partial<DiscoverFilter>) =>
    setDraft(d => ({...d, ...patch}));
  const applyLabel =
    previewCount === undefined
      ? strings.common.loading
      : previewCount === 0
        ? strings.filter.applyEmpty
        : strings.filter.apply(previewCount);

  return (
    <BottomSheet
      visible={visible}
      onClose={onClose}
      title={strings.filter.title}
      testID="filter.sheet"
      footer={
        <>
          <Pressable
            testID="filter.reset"
            accessibilityRole="button"
            onPress={() => setDraft(DEFAULT_FILTER)}
            hitSlop={12}
            style={styles.reset}
          >
            <Text variant="bodyStrong" style={styles.underline}>
              {strings.filter.reset}
            </Text>
          </Pressable>
          <Button
            label={applyLabel}
            testID="filter.apply"
            loading={previewLoading && previewCount === undefined}
            onPress={() => onApply(draft)}
            style={styles.apply}
          />
        </>
      }
    >
      <View style={styles.section}>
        <Text variant="label">{strings.filter.time}</Text>
        <View style={styles.wrap}>
          {TIME_OPTIONS.map(option => (
            <Chip
              key={option.kind}
              label={option.label}
              variant="sheet"
              active={draft.time === option.kind}
              onPress={() => update({time: option.kind})}
              testID={`filter.time.${option.kind}`}
            />
          ))}
        </View>
        {draft.time === 'months' ? (
          <MonthGrid
            options={monthOptions}
            selected={draft.months}
            onToggle={value =>
              update({months: toggleValue(draft.months, value)})
            }
            testID="filter.months"
          />
        ) : null}
      </View>

      <View style={styles.section}>
        <Text variant="label">{strings.filter.category}</Text>
        <View style={styles.wrap}>
          {categories.map(category => (
            <Chip
              key={category.id}
              label={category.name}
              emoji={category.emoji}
              variant="sheet"
              active={draft.categoryIds.includes(category.id)}
              onPress={() =>
                update({
                  categoryIds: toggleValue(draft.categoryIds, category.id),
                })
              }
              testID={`filter.category.${category.id}`}
            />
          ))}
        </View>
      </View>

      <RangeSlider
        value={draft.radiusKm}
        onChange={radiusKm => update({radiusKm})}
        min={MIN_RADIUS_KM}
        max={MAX_RADIUS_KM}
        step={RADIUS_STEP_KM}
        caption={originCaption}
        testID="filter.radius"
      />
    </BottomSheet>
  );
}

const styles = StyleSheet.create({
  section: {gap: 12},
  wrap: {flexDirection: 'row', flexWrap: 'wrap', gap: 10},
  reset: {paddingVertical: 12},
  underline: {textDecorationLine: 'underline'},
  apply: {flex: 1},
});
