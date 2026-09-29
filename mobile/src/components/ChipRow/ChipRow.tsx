import React, {PropsWithChildren} from 'react';
import {ScrollView, StyleSheet} from 'react-native';

export interface ChipRowProps {
  testID: string;
  /** Horizontal padding so the first chip aligns with the page margin. */
  inset?: number;
}

/**
 * Horizontally scrolling chip row without scroll indicator. Dragging the row cancels the
 * press of the chip under the finger, so a drag never toggles a chip (R03-US6).
 */
export function ChipRow({
  children,
  testID,
  inset = 16,
}: PropsWithChildren<ChipRowProps>) {
  return (
    <ScrollView
      testID={testID}
      horizontal
      showsHorizontalScrollIndicator={false}
      keyboardShouldPersistTaps="handled"
      contentContainerStyle={[styles.content, {paddingHorizontal: inset}]}
      style={styles.row}
    >
      {children}
    </ScrollView>
  );
}

const styles = StyleSheet.create({
  row: {flexGrow: 0, overflow: 'visible'},
  content: {gap: 8, paddingVertical: 6},
});
