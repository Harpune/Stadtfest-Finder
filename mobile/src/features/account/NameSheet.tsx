/**
 * Asks for first and last name when the IdP did not provide them (Apple without name
 * sharing, R05-US2). Saved via PATCH /v1/me.
 */
import React, {useState} from 'react';
import {StyleSheet, View} from 'react-native';

import {BottomSheet, Button, Text, TextField, useToast} from '@/components';
import {useAuth} from '@/features/auth/AuthProvider';
import {strings} from '@/strings/de';

import {NAME_MAX_LENGTH, useNameForm} from './nameForm';

export function NameSheet({
  visible,
  onClose,
}: {
  visible: boolean;
  onClose: () => void;
}) {
  const {updateName} = useAuth();
  const toast = useToast();
  const form = useNameForm();
  const [saving, setSaving] = useState(false);

  const save = async () => {
    const names = form.submit();
    if (!names) return;
    setSaving(true);
    const ok = await updateName(names.firstName, names.lastName);
    setSaving(false);
    if (ok) {
      toast(strings.name.saved);
      onClose();
    }
  };

  return (
    <BottomSheet
      visible={visible}
      onClose={onClose}
      title={strings.name.title}
      testID="nameSheet"
      footer={
        <Button
          label={strings.name.save}
          onPress={save}
          loading={saving}
          testID="nameSheet.save"
        />
      }
    >
      <View style={styles.content}>
        <Text variant="body" tone="muted">
          {strings.name.text}
        </Text>
        <TextField
          label={strings.name.firstName}
          value={form.firstName}
          onChangeText={form.setFirstName}
          error={
            form.showErrors && !form.firstNameValid
              ? strings.name.invalid
              : undefined
          }
          maxLength={NAME_MAX_LENGTH}
          autoComplete="given-name"
          textContentType="givenName"
          testID="nameSheet.firstName"
        />
        <TextField
          label={strings.name.lastName}
          value={form.lastName}
          onChangeText={form.setLastName}
          error={
            form.showErrors && !form.lastNameValid
              ? strings.name.invalid
              : undefined
          }
          maxLength={NAME_MAX_LENGTH}
          autoComplete="family-name"
          textContentType="familyName"
          testID="nameSheet.lastName"
        />
      </View>
    </BottomSheet>
  );
}

const styles = StyleSheet.create({content: {gap: 14, paddingTop: 4}});
