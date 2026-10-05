import React from 'react';
import {Pressable, StyleSheet, View} from 'react-native';

import {strings} from '@/strings/de';
import {useTheme} from '@/theme';

import {Icon} from '../Icon/Icon';
import {Text} from '../Text/Text';

export interface ModBannerProps {
  /** Name of the moderator, e.g. "Lena Hofmann" */
  subtitle: string;
  onExit: () => void;
  topInset: number;
  testID: string;
}

/** Fixed banner of the moderation view (turquoise accent, 08-01) with "Beenden". */
export function ModBanner({
  subtitle,
  onExit,
  topInset,
  testID,
}: ModBannerProps) {
  const theme = useTheme();
  const mod = theme.colors.mod;
  return (
    <View
      testID={testID}
      style={[
        styles.banner,
        {backgroundColor: mod.banner, paddingTop: topInset + 8},
      ]}
    >
      <View style={[styles.icon, {backgroundColor: mod.primary}]}>
        <Icon name="shield" size={22} color={mod.onPrimary} />
      </View>
      <View style={styles.text}>
        <Text variant="label" style={{color: mod.text, fontSize: 12}}>
          {strings.mod.banner}
        </Text>
        <Text variant="bodyStrong" numberOfLines={1}>
          {subtitle}
        </Text>
      </View>
      <Pressable
        testID={`${testID}.exit`}
        accessibilityRole="button"
        onPress={onExit}
        style={({pressed}) => [
          styles.exit,
          {borderColor: mod.primary, opacity: pressed ? 0.8 : 1},
        ]}
      >
        <Text variant="bodyStrong" style={{color: mod.text}}>
          {strings.mod.exit}
        </Text>
      </Pressable>
    </View>
  );
}

const styles = StyleSheet.create({
  banner: {
    flexDirection: 'row',
    alignItems: 'center',
    gap: 12,
    paddingHorizontal: 16,
    paddingBottom: 12,
  },
  icon: {
    width: 36,
    height: 36,
    borderRadius: 10,
    alignItems: 'center',
    justifyContent: 'center',
  },
  text: {flex: 1},
  exit: {
    minHeight: 44,
    paddingHorizontal: 14,
    borderRadius: 14,
    borderWidth: 1.5,
    alignItems: 'center',
    justifyContent: 'center',
  },
});
