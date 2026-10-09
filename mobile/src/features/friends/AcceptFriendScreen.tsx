/**
 * Opening a friend link `/freund/{token}` (R12-US2). Guests see the guest hint and continue
 * after the login; signed-in users see "{Vorname} {N.} möchte sich mit dir verbinden".
 */
import {useQuery, useQueryClient} from '@tanstack/react-query';
import {router} from 'expo-router';
import React, {useEffect, useState} from 'react';
import {ActivityIndicator, StyleSheet, View} from 'react-native';
import {useSafeAreaInsets} from 'react-native-safe-area-context';

import {fetchClient} from '@/api/client';
import {Avatar, Button, Icon, IconButton, Text, useToast} from '@/components';
import {useAuth} from '@/features/auth/AuthProvider';
import {strings} from '@/strings/de';
import {useTheme} from '@/theme';

import {FRIENDS_QUERY} from './useFriends';

const s = strings.friends;

type Problem = 'invalid' | 'self' | 'limited' | 'failed';

function problemOf(
  status: number | undefined,
  code: string | undefined,
): Problem {
  if (status === 404) return 'invalid';
  if (code === 'self_link') return 'self';
  if (status === 429) return 'limited';
  return 'failed';
}

const PROBLEM_TEXT: Record<Problem, string> = {
  invalid: s.invalidLink,
  self: s.selfLink,
  limited: s.rateLimited,
  failed: s.failed,
};

export function AcceptFriendScreen({token}: {token: string}) {
  const theme = useTheme();
  const insets = useSafeAreaInsets();
  const toast = useToast();
  const queryClient = useQueryClient();
  const {status, requestAccountAction} = useAuth();
  const [busy, setBusy] = useState(false);
  const signedIn = status === 'signedIn';

  // Guests: remember the link and offer the login (the owner stays hidden until then).
  useEffect(() => {
    if (status === 'guest') requestAccountAction({type: 'friend', token});
  }, [status, token, requestAccountAction]);

  const owner = useQuery({
    queryKey: ['get', '/v1/friend-links/{token}', token],
    enabled: signedIn,
    retry: false,
    queryFn: async () => {
      const {data, error, response} = await fetchClient.GET(
        '/v1/friend-links/{token}',
        {params: {path: {token}}},
      );
      if (!data) throw problemOf(response.status, error?.error);
      return data.owner;
    },
  });

  const close = () =>
    router.canGoBack() ? router.back() : router.replace('/');

  const accept = async () => {
    setBusy(true);
    const result = await fetchClient
      .POST('/v1/friend-links/{token}/accept', {params: {path: {token}}})
      .catch(() => null);
    setBusy(false);
    if (!result?.data) {
      toast(
        PROBLEM_TEXT[problemOf(result?.response.status, result?.error?.error)],
      );
      return;
    }
    toast(s.accepted(result.data.firstName));
    void queryClient.invalidateQueries({queryKey: FRIENDS_QUERY.queryKey});
    router.replace('/freunde');
  };

  let body: React.ReactNode;
  if (!signedIn) {
    body = (
      <Text variant="body" tone="muted" testID="friend.accept.guest">
        {strings.guestHint.friend.text}
      </Text>
    );
  } else if (owner.isPending) {
    body = <ActivityIndicator testID="friend.accept.loading" />;
  } else if (owner.isError) {
    const problem = owner.error as unknown as Problem;
    body = (
      <View style={styles.gap} testID="friend.accept.problem">
        <Text variant="displayS">{PROBLEM_TEXT[problem] ?? s.failed}</Text>
        {problem === 'invalid' ? (
          <Text variant="body" tone="muted">
            {s.invalidLinkText}
          </Text>
        ) : null}
        <Button
          label={strings.common.close}
          variant="secondary"
          onPress={close}
          testID="friend.accept.close"
        />
      </View>
    );
  } else {
    const name =
      `${owner.data.firstName} ${owner.data.lastNameInitial ? `${owner.data.lastNameInitial}.` : ''}`.trim();
    body = (
      <View style={styles.gap}>
        <View style={styles.owner}>
          <Avatar
            initials={`${owner.data.firstName.charAt(0)}${owner.data.lastNameInitial}`.toUpperCase()}
            size={64}
            color={theme.colors.friend.blue}
          />
        </View>
        <Text
          variant="displayS"
          style={styles.center}
          testID="friend.accept.text"
        >
          {s.acceptText(name)}
        </Text>
        <Button
          label={s.accept}
          onPress={() => void accept()}
          loading={busy}
          testID="friend.accept.confirm"
        />
        <Button
          label={s.decline}
          variant="ghost"
          onPress={close}
          testID="friend.accept.decline"
        />
      </View>
    );
  }

  return (
    <View
      style={[
        styles.screen,
        {
          backgroundColor: theme.colors.background,
          paddingTop: insets.top + 8,
          paddingBottom: insets.bottom + 24,
        },
      ]}
      testID="friend.accept.screen"
    >
      <View style={styles.header}>
        <IconButton
          icon={<Icon name="close" size={22} />}
          accessibilityLabel={strings.common.close}
          onPress={close}
          variant="surface"
          testID="friend.accept.back"
        />
        <Text variant="displayM">{s.acceptTitle}</Text>
      </View>
      <View style={styles.body}>{body}</View>
    </View>
  );
}

const styles = StyleSheet.create({
  screen: {flex: 1, paddingHorizontal: 20},
  header: {flexDirection: 'row', alignItems: 'center', gap: 12},
  body: {flex: 1, justifyContent: 'center'},
  gap: {gap: 16},
  owner: {alignItems: 'center'},
  center: {textAlign: 'center'},
});
