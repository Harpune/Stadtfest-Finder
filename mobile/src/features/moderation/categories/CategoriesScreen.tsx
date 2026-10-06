/**
 * Category overview (R09-US1/US2, 10-01): chip preview, rows with count, drag and drop for
 * category admins. Moderators without `category_admin` see the list read-only.
 */
import React, {useEffect, useState} from 'react';
import {ScrollView, StyleSheet, View} from 'react-native';

import {
  Button,
  Chip,
  EmptyState,
  ModCategoryRow,
  Skeleton,
  SortableList,
  Text,
  useToast,
} from '@/components';
import {navigate} from '@/features/navigation/navigate';
import {useAuth} from '@/features/auth/AuthProvider';
import {strings} from '@/strings/de';
import {useTheme} from '@/theme';

import {useExitModeration} from '../useModeration';
import {
  categoryApi,
  ModCategory,
  useModCategories,
  useRefreshCategories,
} from './useModCategories';

const ROW_HEIGHT = 76;
const ROW_GAP = 10;

export function CategoriesScreen() {
  const theme = useTheme();
  const c = theme.colors;
  const toast = useToast();
  const exit = useExitModeration();
  const refresh = useRefreshCategories();
  const {isCategoryAdmin} = useAuth();
  const query = useModCategories();
  // Optimistic order while the server stores it (R09-US2).
  const [order, setOrder] = useState<ModCategory[] | null>(null);
  const categories = order ?? query.data ?? [];

  const status = (query.error as {status?: number} | null)?.status;
  useEffect(() => {
    if (query.isError && status === 403) exit(strings.mod.forbidden);
  }, [query.isError, status, exit]);

  const reorder = async (ids: string[]) => {
    const current = categories.map(category => category.id);
    if (ids.join() === current.join()) return;
    const byId = new Map(categories.map(category => [category.id, category]));
    setOrder(ids.map(id => byId.get(id)).filter(Boolean) as ModCategory[]);
    const result = await categoryApi.order(ids);
    if (result.ok) {
      refresh(result.value);
      toast(strings.mod.categories.orderSaved);
    } else {
      toast(strings.mod.toast.failed);
    }
    setOrder(null);
  };

  const active = categories.filter(category => category.active);

  return (
    <ScrollView contentContainerStyle={styles.content} testID="mod.categories">
      <View style={styles.header}>
        <Text variant="displayXL" accessibilityRole="header">
          {strings.mod.categories.title}
        </Text>
        {isCategoryAdmin ? (
          <Button
            label={strings.mod.categories.add}
            variant="mod"
            size="medium"
            onPress={() => navigate('/mod/kategorien/neu')}
            testID="mod.categories.new"
          />
        ) : null}
      </View>
      <Text variant="body" tone="muted">
        {isCategoryAdmin
          ? strings.mod.categories.intro
          : strings.mod.categories.introReadOnly}
      </Text>

      {active.length > 0 ? (
        <View
          style={[
            styles.preview,
            {backgroundColor: c.surface, borderRadius: theme.radius.block},
          ]}
          testID="mod.categories.preview"
        >
          <Text variant="meta" tone="muted">
            {strings.mod.categories.preview}
          </Text>
          <ScrollView horizontal showsHorizontalScrollIndicator={false}>
            <View style={styles.chips}>
              {active.map(category => (
                <Chip
                  key={category.id}
                  label={category.name}
                  emoji={category.emoji}
                  variant="sheet"
                  // Preview only: looks like the real chip, a tap does nothing.
                  onPress={() => undefined}
                  testID={`mod.categories.preview.${category.id}`}
                />
              ))}
            </View>
          </ScrollView>
        </View>
      ) : null}

      {query.isPending ? (
        <View style={styles.skeleton} testID="mod.categories.loading">
          {[0, 1, 2, 3].map(i => (
            <Skeleton key={i} width="100%" height={ROW_HEIGHT} />
          ))}
        </View>
      ) : query.isError ? (
        <EmptyState
          title={strings.mod.categories.loadFailed}
          text={strings.mod.categories.loadFailedText}
          primary={{
            label: strings.mod.categories.retry,
            onPress: () => void query.refetch(),
            testID: 'mod.categories.retry',
          }}
          testID="mod.categories.error"
        />
      ) : categories.length === 0 ? (
        <EmptyState
          title={strings.mod.categories.empty}
          text={strings.mod.categories.emptyText}
          testID="mod.categories.empty"
        />
      ) : (
        <SortableList
          items={categories}
          keyOf={category => category.id}
          rowHeight={ROW_HEIGHT}
          gap={ROW_GAP}
          enabled={isCategoryAdmin}
          onReorder={ids => void reorder(ids)}
          renderRow={(category, handle) => (
            <ModCategoryRow
              name={category.name}
              emoji={category.emoji}
              color={category.color}
              meta={
                category.active
                  ? strings.mod.categories.events(category.eventCount)
                  : strings.mod.categories.inactive(category.eventCount)
              }
              inactive={!category.active}
              handle={handle}
              onPress={() => navigate(`/mod/kategorien/${category.id}`)}
              testID={`mod.categories.row.${category.id}`}
            />
          )}
          testID="mod.categories.list"
        />
      )}
    </ScrollView>
  );
}

const styles = StyleSheet.create({
  content: {padding: 16, gap: 16, paddingBottom: 32},
  header: {
    flexDirection: 'row',
    alignItems: 'center',
    justifyContent: 'space-between',
    gap: 12,
  },
  preview: {padding: 14, gap: 10},
  chips: {flexDirection: 'row', gap: 8},
  skeleton: {gap: ROW_GAP},
});
