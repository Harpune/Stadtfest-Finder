import React, {PropsWithChildren, useRef} from 'react';
import {StyleSheet, View} from 'react-native';
import ReanimatedSwipeable, {
  SwipeableMethods,
} from 'react-native-gesture-handler/ReanimatedSwipeable';

import {useTheme} from '@/theme';

import {Text} from '../Text/Text';

export interface SwipeToDeleteProps {
  /** Label of the action behind the row and for screen readers, e.g. "Löschen". */
  label: string;
  onDelete: () => void;
  testID: string;
}

/** Width of the revealed action; swiping past `THRESHOLD` deletes on release. */
const ACTION_WIDTH = 96;
const THRESHOLD = 72;

/**
 * Row that is deleted by swiping it to the left (e.g. a notification). Screen readers get
 * the same function as accessibility action, because a swipe is not discoverable for them.
 */
export function SwipeToDelete({
  label,
  onDelete,
  testID,
  children,
}: PropsWithChildren<SwipeToDeleteProps>) {
  const theme = useTheme();
  const c = theme.colors;
  const swipeable = useRef<SwipeableMethods>(null);
  return (
    <ReanimatedSwipeable
      ref={swipeable}
      testID={testID}
      friction={1.5}
      rightThreshold={THRESHOLD}
      overshootRight={false}
      onSwipeableOpen={() => {
        onDelete();
        // Rows that stay (e.g. a cancelled confirmation) slide back.
        swipeable.current?.close();
      }}
      renderRightActions={() => (
        <View
          style={[
            styles.action,
            {
              backgroundColor: c.secondary,
              borderRadius: theme.radius.block,
            },
          ]}
        >
          <Text variant="bodyStrong" style={{color: c.onSecondary}}>
            {label}
          </Text>
        </View>
      )}
    >
      <View
        accessibilityActions={[{name: 'delete', label}]}
        onAccessibilityAction={event => {
          if (event.nativeEvent.actionName === 'delete') onDelete();
        }}
        testID={`${testID}.content`}
      >
        {children}
      </View>
    </ReanimatedSwipeable>
  );
}

const styles = StyleSheet.create({
  action: {
    width: ACTION_WIDTH,
    marginLeft: 8,
    alignItems: 'center',
    justifyContent: 'center',
  },
});
