import React from 'react';
import {Pressable, StyleSheet, View} from 'react-native';

import {strings} from '@/strings/de';
import {useTheme} from '@/theme';

import {Icon} from '../Icon/Icon';
import {Text} from '../Text/Text';

export interface ListEventRowProps {
  /** Day of the start date, e.g. "23". */
  day: string;
  /** Short month, e.g. "NOV". */
  month: string;
  name: string;
  /** "🎄 Ulm · 23. Nov – 22. Dez". */
  meta: string;
  /** Ended events are shown at half opacity. */
  past?: boolean;
  cancelled?: boolean;
  onPress: () => void;
  /** Edit mode (05-04): a pink ✕ replaces the chevron. */
  onRemove?: () => void;
  testID: string;
}

/** Event row of a shared list (05-03/05-04): date block, name, meta line. */
export function ListEventRow({
  day,
  month,
  name,
  meta,
  past = false,
  cancelled = false,
  onPress,
  onRemove,
  testID,
}: ListEventRowProps) {
  const theme = useTheme();
  const c = theme.colors;
  return (
    <Pressable
      testID={testID}
      accessibilityRole="button"
      accessibilityLabel={`${name}, ${meta}${cancelled ? `, ${strings.lists.cancelled}` : ''}`}
      onPress={onPress}
      style={({pressed}) => [
        styles.row,
        {
          backgroundColor: c.surface,
          borderRadius: theme.radius.block,
          opacity: (past ? 0.5 : 1) * (pressed ? 0.85 : 1),
        },
      ]}
    >
      <View style={styles.date}>
        <Text variant="displayM" style={{color: c.secondary}}>
          {day}
        </Text>
        <Text variant="micro" tone="muted">
          {month}
        </Text>
      </View>
      <View style={styles.body}>
        <Text
          variant="displayS"
          numberOfLines={1}
          style={cancelled ? styles.struck : undefined}
        >
          {name}
        </Text>
        <Text variant="meta" tone="muted" numberOfLines={1}>
          {meta}
        </Text>
        {cancelled ? (
          <Text variant="caption" tone="error">
            {strings.lists.cancelled}
          </Text>
        ) : null}
      </View>
      {onRemove ? (
        <Pressable
          testID={`${testID}.remove`}
          accessibilityRole="button"
          accessibilityLabel={strings.lists.removeEvent(name)}
          onPress={onRemove}
          hitSlop={8}
          style={[styles.remove, {backgroundColor: c.errorContainer}]}
        >
          <Icon name="close" size={18} color={c.error} />
        </Pressable>
      ) : (
        <Icon name="chevronRight" size={18} color={c.onSurfaceFaint} />
      )}
    </Pressable>
  );
}

const styles = StyleSheet.create({
  row: {flexDirection: 'row', alignItems: 'center', gap: 12, padding: 14},
  date: {width: 48, alignItems: 'center'},
  body: {flex: 1, gap: 2},
  struck: {textDecorationLine: 'line-through'},
  remove: {
    width: 40,
    height: 40,
    borderRadius: 20,
    alignItems: 'center',
    justifyContent: 'center',
  },
});
