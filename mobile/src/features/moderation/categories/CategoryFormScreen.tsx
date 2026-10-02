/**
 * Create and edit a category (R09-US3/US4, 10-02 to 10-04): live preview of chip and map
 * marker, name, emoji and color presets, active switch, delete with replacement category.
 * Moderators without `category_admin` see it read-only.
 */
import {router} from 'expo-router';
import React, {useState} from 'react';
import {KeyboardAvoidingView, ScrollView, StyleSheet, View} from 'react-native';

import {
  Button,
  Chip,
  ColorPicker,
  Dialog,
  EmojiPicker,
  EventMarker,
  Icon,
  IconButton,
  RadioRow,
  Skeleton,
  SwitchRow,
  Text,
  TextField,
  useToast,
} from '@/components';
import {useAuth} from '@/features/auth/AuthProvider';
import {strings} from '@/strings/de';
import {useTheme} from '@/theme';

import {
  CATEGORY_COLORS,
  CATEGORY_EMOJIS,
  categoryApi,
  CategoryFields,
  ModCategory,
  useModCategories,
  useRefreshCategories,
} from './useModCategories';

type NameError = keyof typeof strings.mod.categories.errors;

function goBack() {
  if (router.canGoBack()) router.back();
  else router.replace('/mod/kategorien');
}

export function CategoryFormScreen({categoryId}: {categoryId: string | null}) {
  const query = useModCategories();
  const category = query.data?.find(item => item.id === categoryId);
  if (categoryId !== null && !category) {
    return (
      <View style={styles.content} testID="mod.category.loading">
        <Skeleton width="100%" height={140} />
        <Skeleton width="100%" height={52} />
      </View>
    );
  }
  return (
    <CategoryForm
      category={category}
      others={(query.data ?? []).filter(item => item.id !== categoryId)}
    />
  );
}

function CategoryForm({
  category,
  others,
}: {
  category: ModCategory | undefined;
  others: ModCategory[];
}) {
  const theme = useTheme();
  const c = theme.colors;
  const toast = useToast();
  const refresh = useRefreshCategories();
  const {isCategoryAdmin} = useAuth();
  const readOnly = !isCategoryAdmin;
  const [fields, setFields] = useState<CategoryFields>(() => ({
    name: category?.name ?? '',
    emoji: (category?.emoji as CategoryFields['emoji']) ?? CATEGORY_EMOJIS[0]!,
    color: (category?.color as CategoryFields['color']) ?? CATEGORY_COLORS[0]!,
    active: category?.active ?? true,
  }));
  const [nameError, setNameError] = useState<NameError | null>(null);
  const [busy, setBusy] = useState<'save' | 'delete' | null>(null);
  const [deleting, setDeleting] = useState(false);
  const [needsReplacement, setNeedsReplacement] = useState(false);
  const [replacement, setReplacement] = useState<string | null>(null);

  const change = (changes: Partial<CategoryFields>) => {
    setFields(current => ({...current, ...changes}));
    if ('name' in changes) setNameError(null);
  };

  const save = async () => {
    if (!fields.name.trim()) {
      setNameError('required');
      return;
    }
    setBusy('save');
    const result = category
      ? await categoryApi.update(category.id, fields)
      : await categoryApi.create(fields);
    setBusy(null);
    if (result.ok) {
      refresh();
      toast(
        category
          ? strings.mod.categories.saved
          : strings.mod.categories.created,
      );
      goBack();
      return;
    }
    const problem = result.error?.fields?.name as NameError | undefined;
    if (
      result.status === 422 &&
      problem &&
      problem in strings.mod.categories.errors
    ) {
      setNameError(problem);
    } else {
      toast(strings.mod.toast.failed);
    }
  };

  const eventCount = category?.eventCount ?? 0;
  const withReplacement = eventCount > 0 || needsReplacement;

  const remove = async () => {
    if (!category) return;
    setBusy('delete');
    const result = await categoryApi.remove(
      category.id,
      withReplacement ? replacement : null,
    );
    setBusy(null);
    if (result.ok) {
      setDeleting(false);
      refresh();
      const target = others.find(item => item.id === replacement);
      toast(
        target && result.value.movedEvents > 0
          ? strings.mod.categories.deletedMoved(
              result.value.movedEvents,
              target.name,
            )
          : strings.mod.categories.deleted,
      );
      goBack();
      return;
    }
    if (result.error?.error === 'replacement_required') {
      // Only deleted events use it: the count shown was 0 (R09-US4).
      setNeedsReplacement(true);
      return;
    }
    setDeleting(false);
    toast(strings.mod.toast.failed);
  };

  const title = readOnly
    ? strings.mod.categories.viewTitle
    : category
      ? strings.mod.categories.editTitle
      : strings.mod.categories.newTitle;

  return (
    <KeyboardAvoidingView
      behavior="padding"
      style={[styles.root, {backgroundColor: c.background}]}
    >
      <View style={[styles.header, {borderBottomColor: c.outline}]}>
        <IconButton
          icon={<Icon name="chevronLeft" size={24} />}
          accessibilityLabel={strings.mod.form.back}
          onPress={goBack}
          variant="surface"
          testID="mod.category.back"
        />
        <Text variant="displayM" numberOfLines={1} style={styles.title}>
          {title}
        </Text>
      </View>

      <ScrollView
        contentContainerStyle={styles.content}
        keyboardShouldPersistTaps="handled"
        testID="mod.category.form"
      >
        {readOnly ? (
          <Text variant="body" tone="muted" testID="mod.category.readOnly">
            {strings.mod.categories.readOnly}
          </Text>
        ) : null}

        <View
          style={[
            styles.preview,
            {backgroundColor: c.surface, borderRadius: theme.radius.sheet},
          ]}
          testID="mod.category.preview"
        >
          <Text variant="meta" tone="muted">
            {strings.mod.categories.formPreview}
          </Text>
          <View style={styles.previewRow}>
            <Chip
              label={fields.name.trim() || strings.mod.categories.title}
              emoji={fields.emoji}
              variant="sheet"
              onPress={() => undefined}
              disabled
              testID="mod.category.preview.chip"
            />
            <EventMarker
              emoji={fields.emoji}
              color={fields.color}
              testID="mod.category.preview.marker"
            />
          </View>
        </View>

        <TextField
          label={strings.mod.categories.name}
          value={fields.name}
          onChangeText={name => change({name})}
          error={
            nameError ? strings.mod.categories.errors[nameError] : undefined
          }
          maxLength={40}
          disabled={readOnly}
          testID="mod.category.name"
        />

        <View style={styles.section}>
          <Text variant="label">{strings.mod.categories.emoji}</Text>
          <EmojiPicker
            options={CATEGORY_EMOJIS}
            value={fields.emoji}
            onChange={emoji =>
              change({emoji: emoji as CategoryFields['emoji']})
            }
            disabled={readOnly}
            testID="mod.category.emoji"
          />
        </View>

        <View style={styles.section}>
          <Text variant="label">{strings.mod.categories.color}</Text>
          <ColorPicker
            options={CATEGORY_COLORS}
            value={fields.color}
            onChange={color =>
              change({color: color as CategoryFields['color']})
            }
            disabled={readOnly}
            testID="mod.category.color"
          />
          <Text variant="caption" tone="muted">
            {strings.mod.categories.colorHint}
          </Text>
        </View>

        <SwitchRow
          label={strings.mod.categories.active}
          hint={strings.mod.categories.activeHint}
          value={fields.active}
          onChange={active => change({active})}
          disabled={readOnly}
          accent="mod"
          testID="mod.category.active"
        />

        {category && !readOnly ? (
          <Button
            label={strings.mod.categories.delete}
            variant="danger"
            onPress={() => {
              setReplacement(null);
              setNeedsReplacement(false);
              setDeleting(true);
            }}
            testID="mod.category.delete"
          />
        ) : null}
      </ScrollView>

      {readOnly ? null : (
        <View
          style={[
            styles.footer,
            {borderTopColor: c.outline, backgroundColor: c.background},
          ]}
        >
          <Button
            label={strings.mod.categories.save}
            variant="mod"
            onPress={() => void save()}
            loading={busy === 'save'}
            testID="mod.category.save"
          />
        </View>
      )}

      <Dialog
        visible={deleting}
        title={strings.mod.categories.deleteDialog.title(category?.name ?? '')}
        text={
          eventCount > 0
            ? strings.mod.categories.deleteDialog.withEvents(eventCount)
            : needsReplacement
              ? strings.mod.categories.deleteDialog.deletedOnly
              : strings.mod.categories.deleteDialog.simple
        }
        confirmLabel={
          !withReplacement
            ? strings.mod.categories.deleteDialog.confirm
            : replacement
              ? strings.mod.categories.deleteDialog.confirmMove
              : strings.mod.categories.deleteDialog.choose
        }
        confirmDisabled={withReplacement && !replacement}
        cancelLabel={strings.mod.cancel}
        tone="danger"
        busy={busy === 'delete'}
        onConfirm={() => void remove()}
        onCancel={() => setDeleting(false)}
        testID="mod.category.deleteDialog"
      >
        {withReplacement ? (
          <View style={styles.section}>
            <Text variant="bodyStrong">
              {strings.mod.categories.deleteDialog.replacement}
            </Text>
            <ScrollView style={styles.replacements}>
              <View style={styles.replacementList}>
                {others.map(other => (
                  <RadioRow
                    key={other.id}
                    label={other.name}
                    emoji={other.emoji}
                    selected={replacement === other.id}
                    onPress={() => setReplacement(other.id)}
                    testID={`mod.category.replacement.${other.id}`}
                  />
                ))}
              </View>
            </ScrollView>
          </View>
        ) : null}
      </Dialog>
    </KeyboardAvoidingView>
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
  title: {flex: 1},
  content: {padding: 16, gap: 22, paddingBottom: 32},
  section: {gap: 10},
  preview: {padding: 18, gap: 12, alignItems: 'center'},
  previewRow: {flexDirection: 'row', alignItems: 'center', gap: 16},
  footer: {padding: 12, borderTopWidth: 1},
  replacements: {maxHeight: 280},
  replacementList: {gap: 8},
});
