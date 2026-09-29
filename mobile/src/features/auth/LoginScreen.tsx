/**
 * Entry screen "Anmelden oder registrieren" (R05-US1). Replaces the form screens 03-04 to
 * 03-06: every button starts the hosted login (Authorization Code + PKCE) in the browser.
 */
import {router} from 'expo-router';
import * as WebBrowser from 'expo-web-browser';
import React, {useState} from 'react';
import {Platform, ScrollView, StyleSheet, View} from 'react-native';
import {useSafeAreaInsets} from 'react-native-safe-area-context';

import {Button, Icon, IconButton, Text} from '@/components';
import {LINK_HOST} from '@/features/event-detail/links';
import {strings} from '@/strings/de';
import {useTheme} from '@/theme';

import {useAuth} from './AuthProvider';
import type {LoginMethod} from './config';

const LEGAL_URLS = {
  terms: `https://${LINK_HOST}/nutzungsbedingungen`,
  privacy: `https://${LINK_HOST}/datenschutz`,
};

export function LoginScreen() {
  const theme = useTheme();
  const insets = useSafeAreaInsets();
  const {login} = useAuth();
  const [busy, setBusy] = useState<LoginMethod | null>(null);

  const start = async (method: LoginMethod) => {
    setBusy(method);
    const outcome = await login(method);
    setBusy(null);
    // Cancel keeps the entry screen open without a toast; errors show a toast.
    if (outcome === 'success' && router.canGoBack()) router.back();
  };

  const button = (
    method: LoginMethod,
    label: string,
    variant: 'primary' | 'secondary' | 'ghost',
  ) => (
    <Button
      label={label}
      variant={variant}
      onPress={() => start(method)}
      loading={busy === method}
      disabled={busy !== null && busy !== method}
      testID={`login.${method}`}
    />
  );

  return (
    <View style={[styles.screen, {backgroundColor: theme.colors.background}]}>
      <ScrollView
        contentContainerStyle={[
          styles.content,
          {paddingTop: insets.top + 12, paddingBottom: insets.bottom + 24},
        ]}
      >
        <View style={styles.close}>
          <IconButton
            icon={<Icon name="close" size={22} />}
            accessibilityLabel={strings.common.close}
            onPress={() => router.back()}
            variant="surface"
            testID="login.close"
          />
        </View>
        <Text variant="displayXL" testID="login.title">
          {strings.login.title}
        </Text>
        <Text variant="body" tone="muted">
          {strings.login.subtitle}
        </Text>
        <View style={styles.buttons}>
          {/* Apple is mandatory on iOS (App Store guideline 4.8), optional on Android. */}
          {Platform.OS === 'ios'
            ? button('apple', strings.login.apple, 'secondary')
            : null}
          {button('google', strings.login.google, 'ghost')}
          {button('email', strings.login.email, 'primary')}
          {button('register', strings.login.register, 'ghost')}
        </View>
        <Text variant="caption" tone="muted" style={styles.legal}>
          {strings.login.legalPrefix}
          <Text
            variant="caption"
            tone="primary"
            accessibilityRole="link"
            testID="login.terms"
            onPress={() => WebBrowser.openBrowserAsync(LEGAL_URLS.terms)}
          >
            {strings.login.terms}
          </Text>
          {strings.login.legalMiddle}
          <Text
            variant="caption"
            tone="primary"
            accessibilityRole="link"
            testID="login.privacy"
            onPress={() => WebBrowser.openBrowserAsync(LEGAL_URLS.privacy)}
          >
            {strings.login.privacy}
          </Text>
          {strings.login.legalSuffix}
        </Text>
      </ScrollView>
    </View>
  );
}

const styles = StyleSheet.create({
  screen: {flex: 1},
  content: {paddingHorizontal: 20, gap: 12},
  close: {alignItems: 'flex-end', marginBottom: 12},
  buttons: {gap: 14, marginTop: 20},
  legal: {textAlign: 'center', marginTop: 16},
});
