import React, {PropsWithChildren} from 'react';
import {KeyboardAvoidingView, Modal, StyleSheet, View} from 'react-native';

import {useTheme} from '@/theme';

import {Button} from '../Button/Button';
import {Text} from '../Text/Text';

export interface DialogProps {
  visible: boolean;
  title: string;
  text: string;
  confirmLabel: string;
  cancelLabel: string;
  onConfirm: () => void;
  onCancel: () => void;
  /** `danger` (pink) for destructive actions such as cancelling or deleting (08-09, 08-10). */
  tone?: 'default' | 'danger' | 'mod';
  /** Shows a spinner in the confirm button and blocks both buttons. */
  busy?: boolean;
  testID: string;
}

/** Centered confirmation dialog with optional content (e.g. a reason field). */
export function Dialog({
  visible,
  title,
  text,
  confirmLabel,
  cancelLabel,
  onConfirm,
  onCancel,
  tone = 'default',
  busy = false,
  testID,
  children,
}: PropsWithChildren<DialogProps>) {
  const theme = useTheme();
  const c = theme.colors;
  return (
    <Modal
      visible={visible}
      transparent
      animationType="fade"
      onRequestClose={onCancel}
      statusBarTranslucent
    >
      {/* Android does not resize a modal for the keyboard, so pad on both platforms. */}
      <KeyboardAvoidingView
        behavior="padding"
        style={[styles.scrim, {backgroundColor: c.scrim}]}
      >
        <View
          testID={testID}
          accessibilityViewIsModal
          style={[
            styles.card,
            {backgroundColor: c.surface, borderRadius: theme.radius.sheet},
          ]}
        >
          <Text variant="displayL" accessibilityRole="header">
            {title}
          </Text>
          <Text variant="body" tone="muted">
            {text}
          </Text>
          {children}
          <View style={styles.actions}>
            <Button
              label={cancelLabel}
              variant="secondary"
              onPress={onCancel}
              disabled={busy}
              testID={`${testID}.cancel`}
              style={styles.cancel}
            />
            <Button
              label={confirmLabel}
              variant={
                tone === 'danger'
                  ? 'destructive'
                  : tone === 'mod'
                    ? 'mod'
                    : 'primary'
              }
              onPress={onConfirm}
              loading={busy}
              testID={`${testID}.confirm`}
              style={styles.confirm}
            />
          </View>
        </View>
      </KeyboardAvoidingView>
    </Modal>
  );
}

const styles = StyleSheet.create({
  scrim: {flex: 1, justifyContent: 'center', padding: 20},
  card: {padding: 22, gap: 14},
  actions: {flexDirection: 'row', gap: 10, marginTop: 4},
  cancel: {flex: 1},
  confirm: {flex: 1.6},
});
