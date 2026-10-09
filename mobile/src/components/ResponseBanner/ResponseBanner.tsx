import React from 'react';
import {Pressable, StyleSheet, View} from 'react-native';

import {strings} from '@/strings/de';
import {useTheme} from '@/theme';

import {Text} from '../Text/Text';

export interface ResponseBannerProps {
  status: 'accepted' | 'declined';
  /** "Ändern": back to open, both buttons appear again. */
  onChange: () => void;
  disabled?: boolean;
  testID: string;
}

/** After answering (06-04): "✓ Du hast zugesagt" (amber) or "Du hast abgesagt" with "Ändern". */
export function ResponseBanner({
  status,
  onChange,
  disabled = false,
  testID,
}: ResponseBannerProps) {
  const theme = useTheme();
  const c = theme.colors;
  const accepted = status === 'accepted';
  const s = strings.invitations;
  return (
    <View
      testID={testID}
      style={[
        styles.banner,
        {
          backgroundColor: accepted ? c.primaryContainer : c.surface,
          borderRadius: theme.radius.buttonLarge,
        },
      ]}
    >
      <Text
        variant="bodyStrong"
        style={[styles.text, {color: accepted ? c.primaryText : c.onSurface}]}
      >
        {accepted ? s.acceptedBanner : s.declinedBanner}
      </Text>
      <Pressable
        onPress={onChange}
        disabled={disabled}
        accessibilityRole="button"
        hitSlop={10}
        testID={`${testID}.change`}
      >
        <Text variant="body" style={styles.link}>
          {s.change}
        </Text>
      </Pressable>
    </View>
  );
}

const styles = StyleSheet.create({
  banner: {
    flex: 1,
    flexDirection: 'row',
    alignItems: 'center',
    justifyContent: 'space-between',
    paddingHorizontal: 18,
    minHeight: 56,
  },
  text: {flex: 1},
  link: {textDecorationLine: 'underline'},
});
