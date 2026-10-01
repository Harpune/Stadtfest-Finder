import React from 'react';
import {Pressable, StyleSheet, View} from 'react-native';

import {useTheme} from '@/theme';

import {Text} from '../Text/Text';

export interface ModTab<T extends string> {
  key: T;
  label: string;
  emoji: string;
}

export interface ModTabBarProps<T extends string> {
  tabs: readonly ModTab<T>[];
  active: T;
  onSelect: (key: T) => void;
  bottomInset: number;
  testID: string;
}

/** Bottom tab bar of the moderation view: "📅 Feste | 🏷️ Kategorien" (08-01). */
export function ModTabBar<T extends string>({
  tabs,
  active,
  onSelect,
  bottomInset,
  testID,
}: ModTabBarProps<T>) {
  const theme = useTheme();
  const c = theme.colors;
  return (
    <View
      testID={testID}
      accessibilityRole="tablist"
      style={[
        styles.bar,
        {
          backgroundColor: c.surface,
          borderTopColor: c.outline,
          paddingBottom: bottomInset + 6,
        },
      ]}
    >
      {tabs.map(tab => {
        const selected = tab.key === active;
        return (
          <Pressable
            key={tab.key}
            testID={`${testID}.${tab.key}`}
            accessibilityRole="tab"
            accessibilityState={{selected}}
            onPress={() => onSelect(tab.key)}
            style={styles.tab}
          >
            <View
              style={[
                styles.iconPill,
                selected ? {backgroundColor: c.mod.container} : null,
              ]}
            >
              <Text style={styles.emoji}>{tab.emoji}</Text>
            </View>
            <Text
              variant="meta"
              style={{
                color: selected ? c.mod.text : c.onSurfaceMuted,
                fontFamily: theme.fonts.semibold,
              }}
            >
              {tab.label}
            </Text>
          </Pressable>
        );
      })}
    </View>
  );
}

const styles = StyleSheet.create({
  bar: {flexDirection: 'row', borderTopWidth: 1, paddingTop: 8},
  tab: {flex: 1, alignItems: 'center', gap: 2, minHeight: 44},
  iconPill: {
    width: 56,
    height: 30,
    borderRadius: 15,
    alignItems: 'center',
    justifyContent: 'center',
  },
  emoji: {fontSize: 18, lineHeight: 22},
});
