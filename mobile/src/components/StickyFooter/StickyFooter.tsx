import React, {PropsWithChildren} from 'react';
import {StyleSheet, View} from 'react-native';
import {useSafeAreaInsets} from 'react-native-safe-area-context';

import {useTheme} from '@/theme';

/** Fixed footer at the bottom edge with a top line (detail: "Route starten", "Einladen"). */
export function StickyFooter({
  children,
  testID,
}: PropsWithChildren<{testID?: string}>) {
  const theme = useTheme();
  const insets = useSafeAreaInsets();
  return (
    <View
      testID={testID}
      style={[
        styles.footer,
        {
          backgroundColor: theme.colors.background,
          borderTopColor: theme.colors.outline,
          paddingBottom: Math.max(insets.bottom, 12),
        },
      ]}
    >
      {children}
    </View>
  );
}

const styles = StyleSheet.create({
  footer: {
    position: 'absolute',
    left: 0,
    right: 0,
    bottom: 0,
    flexDirection: 'row',
    gap: 10,
    paddingHorizontal: 16,
    paddingTop: 12,
    borderTopWidth: 1,
  },
});
