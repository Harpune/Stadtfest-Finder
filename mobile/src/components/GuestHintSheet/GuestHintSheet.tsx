import React from 'react';
import {Pressable, StyleSheet, View} from 'react-native';

import {strings} from '@/strings/de';
import {useTheme} from '@/theme';

import {BottomSheet} from '../BottomSheet/BottomSheet';
import {Button} from '../Button/Button';
import {Icon, IconName} from '../Icon/Icon';
import {Text} from '../Text/Text';

export type GuestHintKind = 'favorite' | 'invite' | 'friend';

const ICONS: Record<GuestHintKind, IconName> = {
  favorite: 'heart',
  invite: 'users',
  friend: 'userPlus',
};

export interface GuestHintSheetProps {
  visible: boolean;
  kind: GuestHintKind;
  onLogin: () => void;
  onDismiss: () => void;
}

/**
 * Non-blocking hint for guests on account actions (screens 03-01 to 03-03): icon tile,
 * title, benefit text, "Anmelden oder registrieren" and "Weiter ohne Konto".
 */
export function GuestHintSheet({
  visible,
  kind,
  onLogin,
  onDismiss,
}: GuestHintSheetProps) {
  const theme = useTheme();
  const c = theme.colors;
  const copy = strings.guestHint[kind];
  return (
    <BottomSheet visible={visible} onClose={onDismiss} testID="guestHint">
      <View style={styles.content}>
        <View
          style={[
            styles.tile,
            {backgroundColor: c.secondaryContainer, borderRadius: 18},
          ]}
        >
          <Icon name={ICONS[kind]} size={26} color={c.secondaryText} />
        </View>
        <Text variant="displayL" testID="guestHint.title">
          {copy.title}
        </Text>
        <Text variant="body" tone="muted">
          {copy.text}
        </Text>
        <Button
          label={strings.guestHint.login}
          onPress={onLogin}
          testID="guestHint.login"
          style={styles.login}
        />
        <Pressable
          testID="guestHint.dismiss"
          accessibilityRole="button"
          onPress={onDismiss}
          style={styles.dismiss}
        >
          <Text variant="bodyStrong" tone="muted">
            {strings.guestHint.dismiss}
          </Text>
        </Pressable>
      </View>
    </BottomSheet>
  );
}

const styles = StyleSheet.create({
  content: {gap: 12, paddingTop: 12},
  tile: {
    width: 56,
    height: 56,
    alignItems: 'center',
    justifyContent: 'center',
    marginBottom: 8,
  },
  login: {marginTop: 12},
  dismiss: {alignSelf: 'center', paddingVertical: 14, paddingHorizontal: 24},
});
