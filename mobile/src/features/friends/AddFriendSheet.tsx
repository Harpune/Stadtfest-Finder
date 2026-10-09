/**
 * "Freund hinzufügen" (R12-US1): QR code of the own friend link, "Link teilen" via the
 * native share sheet and "Link zurücksetzen" with confirmation.
 */
import React from 'react';
import {ActivityIndicator, Alert, Share, StyleSheet, View} from 'react-native';
import QRCode from 'react-native-qrcode-svg';

import {BottomSheet, Button, Text} from '@/components';
import {strings} from '@/strings/de';
import {useTheme} from '@/theme';

import {friendLinkUrl} from './friends';
import {useFriendLink, useRotateFriendLink} from './useFriends';

const s = strings.friends;
const QR_SIZE = 200;

export function AddFriendSheet({
  visible,
  onClose,
}: {
  visible: boolean;
  onClose: () => void;
}) {
  const theme = useTheme();
  const link = useFriendLink(visible);
  const rotate = useRotateFriendLink();
  const url = link.data ? friendLinkUrl(link.data.token) : null;

  const confirmReset = () =>
    Alert.alert(s.resetTitle, s.resetText, [
      {text: s.cancel, style: 'cancel'},
      {
        text: s.resetConfirm,
        style: 'destructive',
        onPress: () => void rotate(),
      },
    ]);

  return (
    <BottomSheet
      visible={visible}
      onClose={onClose}
      title={s.addTitle}
      testID="friends.add.sheet"
    >
      <Text variant="body" tone="muted">
        {s.addText}
      </Text>
      <View style={styles.qrBox}>
        {url ? (
          // White quiet zone in both schemes, so every camera can read the code.
          <View
            style={[styles.qr, {borderRadius: theme.radius.block}]}
            accessible
            accessibilityRole="image"
            accessibilityLabel={s.qrLabel}
            testID="friends.add.qr"
          >
            <QRCode value={url} size={QR_SIZE} ecl="M" />
          </View>
        ) : link.isError ? (
          <Text variant="body" tone="muted">
            {s.failed}
          </Text>
        ) : (
          <ActivityIndicator testID="friends.add.loading" />
        )}
      </View>
      {url ? (
        <Text
          variant="meta"
          tone="muted"
          selectable
          numberOfLines={2}
          style={styles.url}
          testID="friends.add.url"
        >
          {url}
        </Text>
      ) : null}
      <Button
        label={s.share}
        disabled={!url}
        onPress={() => {
          if (url) void Share.share({message: s.shareMessage(url)});
        }}
        testID="friends.add.share"
      />
      <Button
        label={s.reset}
        variant="ghost"
        disabled={!url}
        onPress={confirmReset}
        testID="friends.add.reset"
      />
    </BottomSheet>
  );
}

const styles = StyleSheet.create({
  qrBox: {
    alignItems: 'center',
    justifyContent: 'center',
    minHeight: QR_SIZE + 32,
  },
  qr: {padding: 16, backgroundColor: '#FFFFFF'},
  url: {textAlign: 'center'},
});
