/**
 * Create and edit an event (R07-US3 to US5, 08-02 to 08-10): all fields except images,
 * location by address or pin, program rows, "Als Entwurf" / "Veröffentlichen", and the ⋯
 * menu with cancel and delete.
 */
import {router} from 'expo-router';
import React, {useMemo, useRef, useState} from 'react';
import {
  KeyboardAvoidingView,
  Pressable,
  ScrollView,
  StyleSheet,
  View,
} from 'react-native';

import {$api, fetchClient} from '@/api/client';
import {
  BottomSheet,
  Button,
  Chip,
  DateField,
  Dialog,
  Icon,
  IconButton,
  LocationPicker,
  PinMap,
  Skeleton,
  Spinner,
  Text,
  TextField,
  useToast,
} from '@/components';
import {offlineStyle} from '@/features/discover/mapStyle';
import {useDebouncedValue} from '@/features/discover/useDebouncedValue';
import {type Place, useCategories} from '@/features/discover/useDiscoverData';
import {useTileStyle} from '@/features/discover/useTileStyle';
import {strings} from '@/strings/de';
import {useTheme} from '@/theme';

import {
  draftErrors,
  emptyForm,
  errorsFromServer,
  EventForm,
  FormErrors,
  formFromEvent,
  formToCreate,
  formToPatch,
  ModEventDetail,
  newProgramRow,
  publishErrors,
} from './form';
import {
  modApi,
  ModResult,
  useExitModeration,
  useModEvent,
  useRefreshModeration,
} from './useModeration';

/** Center of the map before a location is set (Ostalb). */
const FALLBACK_CENTER = {lat: 48.84, lon: 10.09};

type Busy = 'draft' | 'publish' | 'cancel' | 'delete' | null;

function goBack() {
  if (router.canGoBack()) router.back();
  else router.replace('/mod');
}

export function ModEventFormScreen({eventId}: {eventId: string | null}) {
  const isNew = eventId === null;
  const detail = useModEvent(eventId);
  const event = detail.data;

  if (!isNew && !event) {
    return (
      <FormSkeleton
        failed={detail.isError}
        onRetry={() => void detail.refetch()}
      />
    );
  }
  return (
    <EventFormBody
      // Remount when a reloaded version comes in (conflict dialog → "Neu laden").
      key={event ? `${event.id}:${event.version}` : 'new'}
      event={event}
      onReload={() => void detail.refetch()}
    />
  );
}

function EventFormBody({
  event,
  onReload,
}: {
  event: ModEventDetail | undefined;
  onReload: () => void;
}) {
  const theme = useTheme();
  const c = theme.colors;
  const toast = useToast();
  const exit = useExitModeration();
  const refresh = useRefreshModeration();
  const categories = useCategories();
  const tileStyle = useTileStyle(theme.scheme);
  const [form, setForm] = useState<EventForm>(() =>
    event ? formFromEvent(event) : emptyForm(),
  );
  const [errors, setErrors] = useState<FormErrors>({});
  const [busy, setBusy] = useState<Busy>(null);
  const [menuOpen, setMenuOpen] = useState(false);
  const [dialog, setDialog] = useState<'cancel' | 'delete' | 'conflict' | null>(
    null,
  );
  const [reason, setReason] = useState('');
  const scroll = useRef<ScrollView>(null);
  const locationY = useRef(0);

  const status = event?.status ?? 'draft';
  const activeIds = useMemo(
    () => new Set((categories.data ?? []).map(category => category.id)),
    [categories.data],
  );
  const update = (changes: Partial<EventForm>) => {
    setForm(current => ({...current, ...changes}));
    // Editing a field removes its error mark.
    setErrors(current => {
      const next = {...current};
      for (const key of Object.keys(changes)) {
        delete next[key as keyof FormErrors];
        if (['lat', 'lon', 'address'].includes(key)) delete next.location;
      }
      return next;
    });
  };

  /** Handles a failed call; returns true if the screen was left. */
  const handleFailure = (result: Extract<ModResult, {ok: false}>): void => {
    if (result.status === 403) {
      exit(strings.mod.forbidden);
      return;
    }
    if (result.status === 409 && result.error?.error === 'version_conflict') {
      setDialog('conflict');
      return;
    }
    if (result.status === 422) {
      setErrors(errorsFromServer(result.error?.fields, result.error?.error));
      toast(strings.mod.toast.fixFields);
      return;
    }
    toast(strings.mod.toast.failed);
  };

  /** Saves the form (create or merge patch); returns the stored event or null. */
  const save = async (): Promise<ModEventDetail | null> => {
    const result = event
      ? await modApi.update(event.id, formToPatch(form), event.version)
      : await modApi.create(formToCreate(form));
    if (!result.ok) {
      handleFailure(result);
      return null;
    }
    return result.event;
  };

  const saveDraft = async () => {
    const found = draftErrors(form);
    if (Object.keys(found).length > 0) {
      setErrors(found);
      toast(strings.mod.toast.fixFields);
      return;
    }
    setBusy('draft');
    try {
      const saved = await save();
      if (!saved) return;
      let final = saved;
      if (saved.status === 'published' || saved.status === 'past') {
        const withdrawn = await modApi.unpublish(saved.id);
        if (!withdrawn.ok) return handleFailure(withdrawn);
        final = withdrawn.event;
        toast(strings.mod.toast.unpublished);
      } else {
        toast(strings.mod.toast.draftSaved);
      }
      refresh(final);
      goBack();
    } finally {
      setBusy(null);
    }
  };

  const publish = async () => {
    const found = publishErrors(form, activeIds);
    if (Object.keys(found).length > 0) {
      setErrors(found);
      toast(strings.mod.toast.fixFields);
      return;
    }
    setBusy('publish');
    try {
      const saved = await save();
      if (!saved) return;
      let final = saved;
      if (saved.status === 'draft') {
        const published = await modApi.publish(saved.id);
        if (!published.ok) {
          refresh(saved);
          return handleFailure(published);
        }
        final = published.event;
        toast(strings.mod.toast.published);
      } else {
        toast(strings.mod.toast.changesPublished);
      }
      refresh(final);
      goBack();
    } finally {
      setBusy(null);
    }
  };

  const cancelEvent = async () => {
    if (!event) return;
    setBusy('cancel');
    try {
      const result = await modApi.cancel(event.id, reason);
      if (!result.ok) {
        setDialog(null);
        return handleFailure(result);
      }
      toast(strings.mod.toast.cancelled(event.favoriteCount));
      setDialog(null);
      refresh(result.event);
      goBack();
    } finally {
      setBusy(null);
    }
  };

  const deleteEvent = async () => {
    if (!event) return;
    setBusy('delete');
    try {
      const result = await modApi.remove(event.id);
      setDialog(null);
      if (!result.ok) {
        if (result.status === 403) return exit(strings.mod.forbidden);
        return toast(strings.mod.toast.failed);
      }
      toast(strings.mod.toast.deleted);
      refresh();
      goBack();
    } finally {
      setBusy(null);
    }
  };

  const statusLabel = strings.mod.status[status];
  const cancelled = status === 'cancelled';
  const published = status === 'published' || status === 'past';

  return (
    <KeyboardAvoidingView
      // Edge-to-edge Android does not resize for the keyboard, so pad on both platforms.
      behavior="padding"
      style={[styles.root, {backgroundColor: c.background}]}
    >
      <View style={[styles.header, {borderBottomColor: c.outline}]}>
        <IconButton
          icon={<Icon name="chevronLeft" size={24} />}
          accessibilityLabel={strings.mod.form.back}
          onPress={goBack}
          variant="surface"
          testID="mod.form.back"
        />
        <View style={styles.headerText}>
          <Text variant="displayM" numberOfLines={1} testID="mod.form.title">
            {event ? form.name || event.name : strings.mod.form.newTitle}
          </Text>
          <Text variant="meta" tone="muted" testID="mod.form.status">
            {strings.mod.form.statusLine(statusLabel)}
          </Text>
        </View>
        {event ? (
          <IconButton
            icon={<Icon name="more" size={24} />}
            accessibilityLabel={strings.mod.form.menu}
            onPress={() => setMenuOpen(true)}
            variant="surface"
            testID="mod.form.menu"
          />
        ) : null}
      </View>

      <ScrollView
        ref={scroll}
        contentContainerStyle={styles.content}
        keyboardShouldPersistTaps="handled"
        testID="mod.form"
      >
        <TextField
          label={strings.mod.form.name}
          value={form.name}
          onChangeText={name => update({name})}
          error={errors.name}
          maxLength={120}
          disabled={cancelled}
          testID="mod.form.name"
        />

        <Section
          label={strings.mod.form.category}
          error={errors.categoryId}
          testID="mod.form.category"
        >
          <View style={styles.wrap}>
            {(categories.data ?? []).map(category => (
              <Chip
                key={category.id}
                label={category.name}
                emoji={category.emoji}
                active={form.categoryId === category.id}
                accent="mod"
                variant="sheet"
                disabled={cancelled}
                onPress={() => update({categoryId: category.id})}
                testID={`mod.form.category.${category.id}`}
              />
            ))}
          </View>
        </Section>

        <Section label={strings.mod.form.period} testID="mod.form.period">
          <View style={styles.row}>
            <DateField
              label={strings.mod.form.start}
              value={form.startDate}
              onChange={startDate => update({startDate})}
              placeholder={strings.mod.form.datePlaceholder}
              invalid={Boolean(errors.startDate)}
              testID="mod.form.start"
            />
            <DateField
              label={strings.mod.form.end}
              value={form.endDate}
              onChange={endDate => update({endDate})}
              placeholder={strings.mod.form.datePlaceholder}
              invalid={Boolean(errors.endDate)}
              minimumDate={form.startDate}
              testID="mod.form.end"
            />
          </View>
          {errors.startDate ? (
            <ErrorText text={errors.startDate} testID="mod.form.start.error" />
          ) : null}
          {errors.endDate ? (
            <ErrorText text={errors.endDate} testID="mod.form.end.error" />
          ) : null}
        </Section>

        <TextField
          label={strings.mod.form.openingHours}
          value={form.openingHours}
          onChangeText={openingHours => update({openingHours})}
          placeholder={strings.mod.form.openingHoursPlaceholder}
          multiline
          testID="mod.form.openingHours"
        />

        <View
          onLayout={event => {
            locationY.current = event.nativeEvent.layout.y;
          }}
        >
          <LocationSection
            form={form}
            error={errors.location}
            disabled={cancelled}
            mapStyle={tileStyle ?? offlineStyle(c.background)}
            onChange={update}
            // Lift the address field to the top so its suggestions stay above the keyboard.
            onAddressFocus={() =>
              scroll.current?.scrollTo({y: locationY.current - 8})
            }
          />
        </View>

        <View style={styles.section}>
          <TextField
            label={strings.mod.form.description}
            value={form.description}
            onChangeText={description => update({description})}
            placeholder={strings.mod.form.descriptionPlaceholder}
            multiline
            maxLength={5000}
            testID="mod.form.description"
          />
          <Text variant="caption" tone="muted">
            {strings.mod.form.privacyHint}
          </Text>
        </View>

        <ProgramEditor
          rows={form.program}
          defaultDate={form.startDate}
          disabled={cancelled}
          onChange={program => update({program})}
        />

        <TextField
          label={strings.mod.form.price}
          value={form.price}
          onChangeText={price => update({price})}
          maxLength={200}
          testID="mod.form.price"
        />
        <View style={styles.section}>
          <TextField
            label={strings.mod.form.directions}
            value={form.transit}
            onChangeText={transit => update({transit})}
            placeholder={strings.mod.form.transitPlaceholder}
            maxLength={500}
            testID="mod.form.transit"
          />
          <TextField
            label={strings.mod.form.parkingPlaceholder}
            hideLabel
            value={form.parking}
            onChangeText={parking => update({parking})}
            placeholder={strings.mod.form.parkingPlaceholder}
            maxLength={500}
            testID="mod.form.parking"
          />
        </View>
        <TextField
          label={strings.mod.form.website}
          value={form.websiteUrl}
          onChangeText={websiteUrl => update({websiteUrl})}
          error={errors.websiteUrl}
          keyboardType="url"
          autoCapitalize="none"
          maxLength={500}
          testID="mod.form.website"
        />
      </ScrollView>

      <View
        style={[
          styles.footer,
          {borderTopColor: c.outline, backgroundColor: c.background},
        ]}
      >
        {cancelled ? null : (
          <Button
            label={strings.mod.form.saveDraft}
            variant="secondary"
            onPress={() => void saveDraft()}
            loading={busy === 'draft'}
            disabled={busy !== null && busy !== 'draft'}
            testID="mod.form.saveDraft"
            // Keeps its full width next to the long "Änderungen veröffentlichen".
            style={styles.secondary}
          />
        )}
        <Button
          label={
            published || cancelled
              ? strings.mod.form.publishChanges
              : strings.mod.form.publish
          }
          variant="mod"
          onPress={() => void publish()}
          loading={busy === 'publish'}
          disabled={busy !== null && busy !== 'publish'}
          testID="mod.form.publish"
          style={styles.primary}
        />
      </View>

      <BottomSheet
        visible={menuOpen}
        onClose={() => setMenuOpen(false)}
        testID="mod.form.menuSheet"
      >
        <View style={styles.menu}>
          {status === 'published' ? (
            <MenuButton
              label={strings.mod.form.cancelEvent}
              onPress={() => {
                setMenuOpen(false);
                setReason('');
                setDialog('cancel');
              }}
              testID="mod.form.menu.cancel"
            />
          ) : null}
          <MenuButton
            label={strings.mod.form.deleteEvent}
            danger
            onPress={() => {
              setMenuOpen(false);
              setDialog('delete');
            }}
            testID="mod.form.menu.delete"
          />
          <Button
            label={strings.mod.form.menuClose}
            variant="ghost"
            onPress={() => setMenuOpen(false)}
            testID="mod.form.menu.close"
          />
        </View>
      </BottomSheet>

      <Dialog
        visible={dialog === 'cancel'}
        title={strings.mod.cancelDialog.title}
        text={strings.mod.cancelDialog.text(
          form.name,
          event?.favoriteCount ?? 0,
        )}
        confirmLabel={strings.mod.cancelDialog.confirm}
        cancelLabel={strings.mod.cancel}
        tone="danger"
        busy={busy === 'cancel'}
        onConfirm={() => void cancelEvent()}
        onCancel={() => setDialog(null)}
        testID="mod.cancelDialog"
      >
        <TextField
          label={strings.mod.cancelDialog.reasonPlaceholder}
          hideLabel
          placeholder={strings.mod.cancelDialog.reasonPlaceholder}
          value={reason}
          onChangeText={setReason}
          multiline
          maxLength={500}
          testID="mod.cancelDialog.reason"
        />
      </Dialog>

      <Dialog
        visible={dialog === 'delete'}
        title={strings.mod.deleteDialog.title}
        text={
          (event?.favoriteCount ?? 0) > 0
            ? `${strings.mod.deleteDialog.text(form.name)} ${strings.mod.deleteDialog.favoritesHint}`
            : strings.mod.deleteDialog.text(form.name)
        }
        confirmLabel={strings.mod.deleteDialog.confirm}
        cancelLabel={strings.mod.cancel}
        tone="danger"
        busy={busy === 'delete'}
        onConfirm={() => void deleteEvent()}
        onCancel={() => setDialog(null)}
        testID="mod.deleteDialog"
      />

      <Dialog
        visible={dialog === 'conflict'}
        title={strings.mod.conflict.title}
        text={strings.mod.conflict.text}
        confirmLabel={strings.mod.conflict.reload}
        cancelLabel={strings.mod.cancel}
        tone="mod"
        onConfirm={() => {
          setDialog(null);
          onReload();
        }}
        onCancel={() => setDialog(null)}
        testID="mod.conflictDialog"
      />
    </KeyboardAvoidingView>
  );
}

function Section({
  label,
  error,
  testID,
  children,
}: React.PropsWithChildren<{label: string; error?: string; testID: string}>) {
  return (
    <View style={styles.section} testID={testID}>
      <Text variant="label">{label}</Text>
      {children}
      {error ? <ErrorText text={error} testID={`${testID}.error`} /> : null}
    </View>
  );
}

function ErrorText({text, testID}: {text: string; testID: string}) {
  return (
    <Text variant="caption" tone="error" testID={testID}>
      {text}
    </Text>
  );
}

function MenuButton({
  label,
  onPress,
  danger = false,
  testID,
}: {
  label: string;
  onPress: () => void;
  danger?: boolean;
  testID: string;
}) {
  const theme = useTheme();
  return (
    <Pressable
      testID={testID}
      accessibilityRole="button"
      onPress={onPress}
      style={({pressed}) => [
        styles.menuButton,
        {
          backgroundColor: theme.colors.surfaceVariant,
          borderRadius: theme.radius.block,
          opacity: pressed ? 0.8 : 1,
        },
      ]}
    >
      <Text
        variant="bodyStrong"
        tone={danger ? 'secondary' : 'default'}
        style={styles.menuLabel}
      >
        {label}
      </Text>
    </Pressable>
  );
}

/** Shortest input that triggers place suggestions. */
const MIN_ADDRESS_QUERY = 3;

/**
 * Location by address with suggestions while typing (08-03), or by a pin chosen on a
 * full-screen map (08-07, reverse geocoding fills the address).
 */
function LocationSection({
  form,
  error,
  disabled,
  mapStyle,
  onChange,
  onAddressFocus,
}: {
  form: EventForm;
  error?: string;
  disabled: boolean;
  mapStyle: Parameters<typeof PinMap>[0]['mapStyle'];
  onChange: (changes: Partial<EventForm>) => void;
  onAddressFocus: () => void;
}) {
  const [typed, setTyped] = useState(false);
  const [pickerOpen, setPickerOpen] = useState(false);
  const text = form.address.trim();
  const query = useDebouncedValue(text, 300);
  const pinMode = form.locationMode === 'pin';
  const searching =
    typed && !pinMode && !disabled && text.length >= MIN_ADDRESS_QUERY;
  const suggestions = $api.useQuery(
    'get',
    '/v1/geocode',
    {params: {query: {q: query, limit: 5}}},
    {
      enabled: searching && query.length >= MIN_ADDRESS_QUERY,
      staleTime: 5 * 60_000,
      retry: false,
    },
  );
  const hasPin = form.lat !== null && form.lon !== null;
  const pending = query !== text || suggestions.isFetching;

  const pickPin = async (lat: number, lon: number) => {
    const rounded = {
      lat: Math.round(lat * 1e5) / 1e5,
      lon: Math.round(lon * 1e5) / 1e5,
    };
    setTyped(false);
    onChange({...rounded, locationMode: 'pin'});
    const {data} = await fetchClient
      .GET('/v1/geocode/reverse', {params: {query: rounded}})
      .catch(() => ({data: undefined}));
    onChange({
      postalCode: data?.postalCode ?? null,
      city: data?.city ?? '',
      // Keep a typed address; otherwise fill it from the pin.
      ...(form.address.trim()
        ? {}
        : {
            address:
              data?.label ??
              strings.mod.form.pinLabel(
                rounded.lat.toFixed(4),
                rounded.lon.toFixed(4),
              ),
            place: '',
          }),
    });
  };

  return (
    <Section
      label={strings.mod.form.location}
      error={error}
      testID="mod.form.location"
    >
      <View style={styles.wrap}>
        {(['address', 'pin'] as const).map(mode => (
          <Chip
            key={mode}
            label={
              mode === 'address'
                ? strings.mod.form.locationAddress
                : strings.mod.form.locationPin
            }
            active={form.locationMode === mode}
            accent="mod"
            variant="sheet"
            disabled={disabled}
            onPress={() => {
              onChange({locationMode: mode});
              if (mode === 'pin') setPickerOpen(true);
            }}
            testID={`mod.form.location.${mode}`}
          />
        ))}
      </View>
      <TextField
        label={strings.mod.form.locationAddress}
        hideLabel
        value={form.address}
        onChangeText={address => {
          setTyped(true);
          onChange({address});
        }}
        placeholder={strings.mod.form.addressPlaceholder}
        onFocus={onAddressFocus}
        disabled={disabled || pinMode}
        testID="mod.form.address"
      />
      {searching ? (
        <AddressSuggestions
          places={suggestions.data ?? []}
          pending={pending}
          failed={suggestions.isError}
          onPick={place => {
            setTyped(false);
            const [first] = place.label.split(',');
            onChange({
              address: place.label,
              place: place.kind === 'address' ? (first ?? '').trim() : '',
              city: place.city,
              postalCode: place.postalCode ?? null,
              lat: place.lat,
              lon: place.lon,
            });
          }}
        />
      ) : null}
      <PinMap
        lat={form.lat}
        lon={form.lon}
        fallback={FALLBACK_CENTER}
        mapStyle={mapStyle}
        active={pinMode && !disabled}
        onPress={disabled ? undefined : () => setPickerOpen(true)}
        pressLabel={
          hasPin ? strings.mod.form.pinEdit : strings.mod.form.pinHint
        }
        caption={
          pinMode || !hasPin
            ? hasPin
              ? strings.mod.form.pinEdit
              : strings.mod.form.pinHint
            : `${form.lat?.toFixed(4)}, ${form.lon?.toFixed(4)}`
        }
        invalid={Boolean(error)}
        testID="mod.form.map"
      />
      <LocationPicker
        visible={pickerOpen}
        start={
          form.lat !== null && form.lon !== null
            ? {lat: form.lat, lon: form.lon}
            : FALLBACK_CENTER
        }
        exact={hasPin}
        mapStyle={mapStyle}
        onConfirm={(lat, lon) => {
          setPickerOpen(false);
          void pickPin(lat, lon);
        }}
        onCancel={() => setPickerOpen(false)}
        testID="mod.form.picker"
      />
    </Section>
  );
}

/** Suggestions below the address field with searching, empty and error states. */
function AddressSuggestions({
  places,
  pending,
  failed,
  onPick,
}: {
  places: Place[];
  pending: boolean;
  failed: boolean;
  onPick: (place: Place) => void;
}) {
  const theme = useTheme();
  const c = theme.colors;
  let status: string | null = null;
  if (places.length === 0) {
    if (pending) status = strings.mod.form.addressSearching;
    else if (failed) status = strings.mod.form.addressUnavailable;
    else status = strings.mod.form.addressNoMatch;
  }
  return (
    <View
      style={[
        styles.suggestions,
        {
          backgroundColor: c.surface,
          borderColor: c.outline,
          borderRadius: theme.radius.input,
        },
      ]}
      testID="mod.form.address.suggestions"
    >
      {status ? (
        <View style={styles.suggestion}>
          {pending ? <Spinner color={c.mod.primary} /> : null}
          <Text
            variant="meta"
            tone="muted"
            style={styles.suggestionText}
            testID="mod.form.address.status"
          >
            {status}
          </Text>
        </View>
      ) : (
        places.map((place, index) => (
          <Pressable
            key={`${place.lat},${place.lon},${place.label}`}
            accessibilityRole="button"
            onPress={() => onPick(place)}
            style={({pressed}) => [
              styles.suggestion,
              index > 0 && {
                borderTopWidth: StyleSheet.hairlineWidth,
                borderTopColor: c.outline,
              },
              pressed && {backgroundColor: c.surfaceVariant},
            ]}
            testID={`mod.form.address.suggestion.${index}`}
          >
            <Icon name="pin" size={18} color={c.mod.primary} />
            <Text
              variant="body"
              numberOfLines={2}
              style={styles.suggestionText}
            >
              {place.label}
            </Text>
          </Pressable>
        ))
      )}
    </View>
  );
}

/** Program rows "Tag, Zeit" and "Programmpunkt" with ✕ and "+ Programmpunkt" (08-04). */
function ProgramEditor({
  rows,
  defaultDate,
  disabled,
  onChange,
}: {
  rows: EventForm['program'];
  defaultDate: string | null;
  disabled: boolean;
  onChange: (rows: EventForm['program']) => void;
}) {
  const theme = useTheme();
  const c = theme.colors;
  const set = (key: string, changes: Partial<EventForm['program'][number]>) =>
    onChange(rows.map(row => (row.key === key ? {...row, ...changes} : row)));
  return (
    <View style={styles.section} testID="mod.form.program">
      <Text variant="label">{strings.mod.form.program}</Text>
      {rows.map((row, index) => (
        <View
          key={row.key}
          style={[styles.programRow, {borderColor: c.outline}]}
        >
          <View style={styles.row}>
            <DateField
              label={strings.mod.form.programDay}
              value={row.date}
              onChange={date => set(row.key, {date})}
              placeholder={strings.mod.form.datePlaceholder}
              testID={`mod.form.program.${index}.date`}
            />
            <View style={styles.flex}>
              <TextField
                label={strings.mod.form.programTime}
                value={row.timeLabel}
                onChangeText={timeLabel => set(row.key, {timeLabel})}
                placeholder="11 Uhr"
                maxLength={40}
                testID={`mod.form.program.${index}.time`}
              />
            </View>
          </View>
          <View style={styles.programTitle}>
            <View style={styles.flex}>
              <TextField
                label={strings.mod.form.programTitle}
                hideLabel
                value={row.title}
                onChangeText={title => set(row.key, {title})}
                placeholder={strings.mod.form.programTitle}
                maxLength={120}
                testID={`mod.form.program.${index}.title`}
              />
            </View>
            <IconButton
              icon={<Icon name="close" size={20} color={c.secondary} />}
              accessibilityLabel={strings.mod.form.programRemove}
              onPress={() => onChange(rows.filter(r => r.key !== row.key))}
              variant="surface"
              testID={`mod.form.program.${index}.remove`}
            />
          </View>
        </View>
      ))}
      {disabled || rows.length >= 50 ? null : (
        <Pressable
          accessibilityRole="button"
          onPress={() => onChange([...rows, newProgramRow(defaultDate)])}
          style={[
            styles.addRow,
            {borderColor: c.outline, borderRadius: theme.radius.input},
          ]}
          testID="mod.form.program.add"
        >
          <Text variant="bodyStrong" tone="mod">
            {strings.mod.form.programAdd}
          </Text>
        </Pressable>
      )}
    </View>
  );
}

function FormSkeleton({
  failed,
  onRetry,
}: {
  failed: boolean;
  onRetry: () => void;
}) {
  return (
    <View style={styles.content} testID="mod.form.loading">
      {failed ? (
        <Button
          label={strings.mod.retry}
          onPress={onRetry}
          variant="mod"
          testID="mod.form.retry"
        />
      ) : (
        [0, 1, 2, 3].map(i => (
          <View key={i} style={styles.section}>
            <Skeleton width={90} height={14} />
            <Skeleton width="100%" height={52} />
          </View>
        ))
      )}
    </View>
  );
}

const styles = StyleSheet.create({
  root: {flex: 1},
  header: {
    flexDirection: 'row',
    alignItems: 'center',
    gap: 12,
    paddingHorizontal: 16,
    paddingVertical: 10,
    borderBottomWidth: 1,
  },
  headerText: {flex: 1},
  content: {padding: 16, gap: 22, paddingBottom: 32},
  section: {gap: 8},
  wrap: {flexDirection: 'row', flexWrap: 'wrap', gap: 8},
  row: {flexDirection: 'row', gap: 10},
  flex: {flex: 1},
  suggestions: {borderWidth: 1, overflow: 'hidden'},
  suggestion: {
    flexDirection: 'row',
    alignItems: 'center',
    gap: 10,
    minHeight: 48,
    paddingHorizontal: 14,
    paddingVertical: 8,
  },
  suggestionText: {flex: 1},
  programRow: {gap: 8, borderBottomWidth: 1, paddingBottom: 10},
  programTitle: {flexDirection: 'row', alignItems: 'center', gap: 8},
  addRow: {
    minHeight: 52,
    borderWidth: 1.5,
    borderStyle: 'dashed',
    alignItems: 'center',
    justifyContent: 'center',
  },
  footer: {flexDirection: 'row', gap: 10, padding: 12, borderTopWidth: 1},
  primary: {flex: 1},
  secondary: {flexShrink: 0},
  menu: {gap: 10, paddingBottom: 8},
  menuButton: {minHeight: 56, justifyContent: 'center', paddingHorizontal: 18},
  menuLabel: {fontSize: 17},
});
