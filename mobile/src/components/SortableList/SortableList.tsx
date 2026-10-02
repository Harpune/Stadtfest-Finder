import React, {ReactNode, useEffect} from 'react';
import {StyleSheet, View} from 'react-native';
import {Gesture, GestureDetector} from 'react-native-gesture-handler';
import Animated, {
  SharedValue,
  useAnimatedReaction,
  useAnimatedStyle,
  useSharedValue,
  withTiming,
} from 'react-native-reanimated';
import {scheduleOnRN} from 'react-native-worklets';

import {strings} from '@/strings/de';
import {useTheme} from '@/theme';

import {Icon} from '../Icon/Icon';

/** Duration of the other rows moving aside (R09-US2). */
const MOVE_MS = 200;

type Positions = Record<string, number>;

export interface SortableListProps<T> {
  items: readonly T[];
  keyOf: (item: T) => string;
  /** Fixed height of a row; rows are positioned absolutely. */
  rowHeight: number;
  gap?: number;
  /** Renders a row; `handle` is the drag grip to place inside it. */
  renderRow: (item: T, handle: ReactNode) => ReactNode;
  /** Called with all keys in the new order after a drop or an accessibility move. */
  onReorder: (keys: string[]) => void;
  /** Without it there are no grips and nothing can be moved (read-only). */
  enabled?: boolean;
  testID: string;
}

function indexMap(keys: readonly string[]): Positions {
  return Object.fromEntries(keys.map((key, index) => [key, index]));
}

function ordered(positions: Positions): string[] {
  'worklet';
  return Object.keys(positions).sort((a, b) => positions[a]! - positions[b]!);
}

function move(positions: Positions, key: string, to: number): Positions {
  'worklet';
  const from = positions[key]!;
  const next: Positions = {};
  for (const other of Object.keys(positions)) {
    const p = positions[other]!;
    if (other === key) next[other] = to;
    else if (from < to && p > from && p <= to) next[other] = p - 1;
    else if (from > to && p < from && p >= to) next[other] = p + 1;
    else next[other] = p;
  }
  return next;
}

/**
 * List sorted by dragging the grip (Reanimated + Gesture Handler, 10-01): the row lifts with
 * a shadow and a turquoise border, the others move aside in 200 ms. Screen readers move rows
 * with the actions "nach oben" / "nach unten" on the grip.
 */
export function SortableList<T>({
  items,
  keyOf,
  rowHeight,
  gap = 0,
  renderRow,
  onReorder,
  enabled = true,
  testID,
}: SortableListProps<T>) {
  const keys = items.map(keyOf);
  const positions = useSharedValue<Positions>(indexMap(keys));
  const signature = keys.join('|');
  useEffect(() => {
    positions.value = indexMap(signature ? signature.split('|') : []);
  }, [signature, positions]);
  const step = rowHeight + gap;

  const moveBy = (key: string, delta: number) => {
    const from = keys.indexOf(key);
    const to = from + delta;
    if (from < 0 || to < 0 || to >= keys.length) return;
    onReorder(ordered(move(indexMap(keys), key, to)));
  };

  return (
    <View
      testID={testID}
      style={{height: Math.max(items.length * step - gap, 0)}}
    >
      {items.map((item, index) => {
        const key = keyOf(item);
        return (
          <SortableRow
            key={key}
            id={key}
            initialIndex={index}
            positions={positions}
            step={step}
            height={rowHeight}
            count={items.length}
            enabled={enabled}
            onDrop={onReorder}
            onMoveBy={delta => moveBy(key, delta)}
            testID={`${testID}.row.${index}`}
            render={handle => renderRow(item, handle)}
          />
        );
      })}
    </View>
  );
}

interface SortableRowProps {
  id: string;
  initialIndex: number;
  positions: SharedValue<Positions>;
  step: number;
  height: number;
  count: number;
  enabled: boolean;
  onDrop: (keys: string[]) => void;
  onMoveBy: (delta: number) => void;
  render: (handle: ReactNode) => ReactNode;
  testID: string;
}

function SortableRow({
  id,
  initialIndex,
  positions,
  step,
  height,
  count,
  enabled,
  onDrop,
  onMoveBy,
  render,
  testID,
}: SortableRowProps) {
  const theme = useTheme();
  const c = theme.colors;
  const top = useSharedValue(initialIndex * step);
  const start = useSharedValue(0);
  const dragging = useSharedValue(false);

  // Follow position changes made by the dragged row (or a new order from the server).
  useAnimatedReaction(
    () => positions.value[id],
    (index, previous) => {
      if (index === undefined || index === previous || dragging.value) return;
      top.value = withTiming(index * step, {duration: MOVE_MS});
    },
  );

  const pan = Gesture.Pan()
    .enabled(enabled)
    .activeOffsetY([-4, 4])
    .onStart(() => {
      dragging.value = true;
      start.value = top.value;
    })
    .onUpdate(event => {
      const y = Math.min(
        Math.max(start.value + event.translationY, 0),
        (count - 1) * step,
      );
      top.value = y;
      const to = Math.round(y / step);
      if (to !== positions.value[id])
        positions.value = move(positions.value, id, to);
    })
    .onFinalize(() => {
      const index = positions.value[id] ?? 0;
      top.value = withTiming(index * step, {duration: MOVE_MS});
      if (dragging.value) scheduleOnRN(onDrop, ordered(positions.value));
      dragging.value = false;
    });

  const rowStyle = useAnimatedStyle(() => ({
    top: top.value,
    zIndex: dragging.value ? 10 : 0,
    borderColor: dragging.value ? c.mod.primary : 'transparent',
    shadowOpacity: dragging.value ? 0.35 : 0,
    elevation: dragging.value ? 8 : 0,
    transform: [
      {scale: withTiming(dragging.value ? 1.02 : 1, {duration: 120})},
    ],
  }));

  const handle = enabled ? (
    <GestureDetector gesture={pan}>
      <View
        accessible
        accessibilityRole="adjustable"
        accessibilityLabel={strings.sortable.handle}
        accessibilityActions={[
          {name: 'increment', label: strings.sortable.down},
          {name: 'decrement', label: strings.sortable.up},
        ]}
        onAccessibilityAction={event =>
          onMoveBy(event.nativeEvent.actionName === 'increment' ? 1 : -1)
        }
        hitSlop={8}
        style={styles.handle}
        testID={`${testID}.handle`}
      >
        <Icon name="grip" size={22} color={c.onSurfaceFaint} />
      </View>
    </GestureDetector>
  ) : null;

  return (
    <Animated.View
      testID={testID}
      style={[
        styles.row,
        {height, borderRadius: theme.radius.block, shadowColor: '#000'},
        rowStyle,
      ]}
    >
      {render(handle)}
    </Animated.View>
  );
}

const styles = StyleSheet.create({
  row: {
    position: 'absolute',
    left: 0,
    right: 0,
    borderWidth: 2,
    shadowOffset: {width: 0, height: 8},
    shadowRadius: 16,
  },
  handle: {
    width: 32,
    height: 44,
    alignItems: 'center',
    justifyContent: 'center',
  },
});
