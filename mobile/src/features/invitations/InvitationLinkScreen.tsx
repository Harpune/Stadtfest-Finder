/**
 * Opening an invitation link `/e/{token}` (R14-US3). Guests see the guest hint and continue
 * after the login; signed-in users see host and event and accept: they become friends with
 * the host and an invitee. The own link leads to the own overview.
 */
import {useQuery, useQueryClient} from '@tanstack/react-query';
import {router} from 'expo-router';
import React, {useEffect, useState} from 'react';
import {ActivityIndicator, StyleSheet, View} from 'react-native';
import {useSafeAreaInsets} from 'react-native-safe-area-context';

import {fetchClient} from '@/api/client';
import {
  Avatar,
  Button,
  EventHeaderCard,
  Icon,
  IconButton,
  Text,
  useToast,
} from '@/components';
import {useAuth} from '@/features/auth/AuthProvider';
import {FRIENDS_QUERY} from '@/features/friends/useFriends';
import {strings} from '@/strings/de';
import {useTheme} from '@/theme';

import {eventMetaText} from './format';
import {
  InvitationProblem,
  PROBLEM_TEXT,
  problemOf,
  receivedInvitationKey,
} from './useInvitations';

const s = strings.invitations;

export function InvitationLinkScreen({token}: {token: string}) {
  const theme = useTheme();
  const insets = useSafeAreaInsets();
  const toast = useToast();
  const queryClient = useQueryClient();
  const {status, requestAccountAction} = useAuth();
  const [busy, setBusy] = useState(false);
  const signedIn = status === 'signedIn';

  useEffect(() => {
    if (status === 'guest')
      requestAccountAction({type: 'invitationLink', token});
  }, [status, token, requestAccountAction]);

  const preview = useQuery({
    queryKey: ['get', '/v1/invitation-links/{token}', token],
    enabled: signedIn,
    retry: false,
    queryFn: async () => {
      const {data, error, response} = await fetchClient.GET(
        '/v1/invitation-links/{token}',
        {params: {path: {token}}},
      );
      if (!data) throw problemOf(response.status, error?.error);
      return data;
    },
  });

  // The own link: straight to the own overview.
  useEffect(() => {
    if (preview.data?.own) {
      router.replace({
        pathname: '/einladen/[eventId]',
        params: {eventId: preview.data.event.id},
      });
    }
  }, [preview.data]);

  const close = () =>
    router.canGoBack() ? router.back() : router.replace('/');

  const accept = async () => {
    setBusy(true);
    const result = await fetchClient
      .POST('/v1/invitation-links/{token}/accept', {params: {path: {token}}})
      .catch(() => null);
    setBusy(false);
    if (!result?.data) {
      toast(
        PROBLEM_TEXT[problemOf(result?.response.status, result?.error?.error)],
      );
      return;
    }
    queryClient.setQueryData(
      receivedInvitationKey(result.data.id),
      result.data,
    );
    void queryClient.invalidateQueries({queryKey: FRIENDS_QUERY.queryKey});
    router.replace({pathname: '/einladung/[id]', params: {id: result.data.id}});
  };

  let body: React.ReactNode;
  if (!signedIn) {
    body = (
      <Text variant="body" tone="muted" testID="invitationLink.guest">
        {strings.guestHint.invite.text}
      </Text>
    );
  } else if (preview.isPending || preview.data?.own) {
    body = <ActivityIndicator testID="invitationLink.loading" />;
  } else if (preview.isError) {
    const problem = preview.error as unknown as InvitationProblem;
    body = (
      <View style={styles.gap} testID="invitationLink.problem">
        <Text variant="displayS">
          {problem === 'notFound'
            ? s.invalidLink
            : (PROBLEM_TEXT[problem] ?? s.failed)}
        </Text>
        <Button
          label={strings.common.close}
          variant="secondary"
          onPress={close}
          testID="invitationLink.close"
        />
      </View>
    );
  } else {
    const {host, event} = preview.data;
    const name =
      `${host.firstName} ${host.lastNameInitial ? `${host.lastNameInitial}.` : ''}`.trim();
    body = (
      <View style={styles.gap}>
        <View style={styles.center}>
          <Avatar
            initials={`${host.firstName.charAt(0)}${host.lastNameInitial}`.toUpperCase()}
            size={64}
            color={theme.colors.friend.blue}
          />
        </View>
        <Text
          variant="displayS"
          style={styles.centerText}
          testID="invitationLink.text"
        >
          {s.linkFrom(name)}
        </Text>
        <EventHeaderCard
          name={event.name}
          meta={eventMetaText(event)}
          imageUrl={event.coverImage?.thumbUrl}
          testID="invitationLink.event"
        />
        <Text variant="body" tone="muted" style={styles.centerText}>
          {s.linkText}
        </Text>
        <Button
          label={s.linkAccept}
          onPress={() => void accept()}
          loading={busy}
          testID="invitationLink.accept"
        />
        <Button
          label={s.linkDecline}
          variant="ghost"
          onPress={close}
          testID="invitationLink.decline"
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
      testID="invitationLink.screen"
    >
      <View style={styles.header}>
        <IconButton
          icon={<Icon name="close" size={22} />}
          accessibilityLabel={strings.common.close}
          onPress={close}
          variant="surface"
          testID="invitationLink.back"
        />
        <Text variant="displayM">{s.linkTitle}</Text>
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
  center: {alignItems: 'center'},
  centerText: {textAlign: 'center'},
});
