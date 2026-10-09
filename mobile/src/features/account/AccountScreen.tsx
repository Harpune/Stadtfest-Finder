/**
 * Account page (R05-US5/US6): change name, delete account (Art. 17 GDPR, App Store duty).
 * Design gap: built in the style of the existing screens.
 */
import {router} from 'expo-router';
import React, {useState} from 'react';
import {ScrollView, StyleSheet, View} from 'react-native';
import {useSafeAreaInsets} from 'react-native-safe-area-context';

import {
  Avatar,
  Button,
  Icon,
  IconButton,
  Text,
  TextField,
  useToast,
} from '@/components';
import {initialsOf, useAuth} from '@/features/auth/AuthProvider';
import {strings} from '@/strings/de';
import {useTheme} from '@/theme';

import {NAME_MAX_LENGTH, useNameForm} from './nameForm';
import {useConfirmDeleteAccount} from './useConfirmDeleteAccount';

export function AccountScreen() {
  const theme = useTheme();
  const insets = useSafeAreaInsets();
  const toast = useToast();
  const {user, email, updateName} = useAuth();
  const form = useNameForm(user?.firstName ?? '', user?.lastName ?? '');
  const [saving, setSaving] = useState(false);
  const {confirm: confirmDelete, deleting} = useConfirmDeleteAccount();

  const save = async () => {
    const names = form.submit();
    if (!names) return;
    setSaving(true);
    const ok = await updateName(names.firstName, names.lastName);
    setSaving(false);
    if (ok) toast(strings.name.saved);
  };

  return (
    <View style={[styles.screen, {backgroundColor: theme.colors.background}]}>
      <ScrollView
        keyboardShouldPersistTaps="handled"
        contentContainerStyle={[
          styles.content,
          {paddingTop: insets.top + 8, paddingBottom: insets.bottom + 24},
        ]}
      >
        <View style={styles.header}>
          <IconButton
            icon={<Icon name="chevronLeft" size={22} />}
            accessibilityLabel={strings.detail.back}
            onPress={() => router.back()}
            variant="surface"
            testID="account.back"
          />
          <Text variant="displayM">{strings.account.title}</Text>
        </View>
        <View style={styles.identity}>
          <Avatar initials={initialsOf(user)} size={64} />
          {email ? (
            <View style={styles.email}>
              <Text variant="label">{strings.account.email}</Text>
              <Text variant="body" testID="account.email">
                {email}
              </Text>
              <Text variant="caption" tone="muted">
                {strings.account.emailHint}
              </Text>
            </View>
          ) : null}
        </View>
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
          testID="account.firstName"
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
          testID="account.lastName"
        />
        <Button
          label={strings.name.save}
          onPress={save}
          loading={saving}
          testID="account.save"
        />
        <Button
          label={strings.account.delete}
          variant="danger"
          onPress={confirmDelete}
          loading={deleting}
          testID="account.delete"
          style={styles.delete}
        />
      </ScrollView>
    </View>
  );
}

const styles = StyleSheet.create({
  screen: {flex: 1},
  content: {paddingHorizontal: 20, gap: 16},
  header: {flexDirection: 'row', alignItems: 'center', gap: 12},
  identity: {flexDirection: 'row', alignItems: 'center', gap: 16},
  email: {flex: 1, gap: 2},
  delete: {marginTop: 24},
});
