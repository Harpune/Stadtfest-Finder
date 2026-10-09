/**
 * A received invitation (R14-US5, screens 06-03 and 06-04): host, message, event card,
 * the other invitees and "Absagen" / "Zusagen"; after answering a banner with "Ändern".
 */
import {router} from 'expo-router';
import React, {useState} from 'react';
import {ActivityIndicator, ScrollView, StyleSheet, View} from 'react-native';
import {useSafeAreaInsets} from 'react-native-safe-area-context';

import {
  Avatar,
  Button,
  Icon,
  IconButton,
  InvitationEventCard,
  InviteeRow,
  MessageBubble,
  ResponseBanner,
  StickyFooter,
  Text,
} from '@/components';
import {todayInBerlin} from '@/features/events/dates';
import {friendColor, initialsOfName} from '@/features/friends/friends';
import {navigate} from '@/features/navigation/navigate';
import {formatNotificationTime} from '@/features/notifications/time';
import {strings} from '@/strings/de';
import {useTheme} from '@/theme';

import {eventMetaText, fullName, whenText} from './format';
import {
  InvitationProblem,
  InviteeStatus,
  PROBLEM_TEXT,
  ReceivedInvitation,
  useReceivedInvitation,
  useRespond,
} from './useInvitations';

const s = strings.invitations;
const FOOTER_SPACE = 110;

export function ReceivedInvitationScreen({
  invitationId,
}: {
  invitationId: string;
}) {
  const theme = useTheme();
  const insets = useSafeAreaInsets();
  const invitation = useReceivedInvitation(invitationId);

  const back = () => (router.canGoBack() ? router.back() : router.replace('/'));

  let content: React.ReactNode;
  if (invitation.isPending) {
    content = (
      <ActivityIndicator style={styles.loading} testID="received.loading" />
    );
  } else if (invitation.isError || !invitation.data) {
    const problem = invitation.error as unknown as InvitationProblem;
    content = (
      <View style={styles.padded} testID="received.problem">
        <Text variant="displayS">{PROBLEM_TEXT[problem] ?? s.failed}</Text>
        <Button
          label={strings.common.close}
          variant="secondary"
          onPress={back}
          testID="received.close"
        />
      </View>
    );
  } else {
    content = <Content invitation={invitation.data} />;
  }

  return (
    <View
      style={[
        styles.screen,
        {backgroundColor: theme.colors.background, paddingTop: insets.top + 8},
      ]}
      testID="received.screen"
    >
      <View style={styles.header}>
        <IconButton
          icon={<Icon name="chevronLeft" size={22} />}
          accessibilityLabel={strings.detail.back}
          onPress={back}
          variant="surface"
          testID="received.back"
        />
        <Text variant="displayL">{s.receivedTitle}</Text>
      </View>
      {content}
    </View>
  );
}

function Content({invitation}: {invitation: ReceivedInvitation}) {
  const theme = useTheme();
  const insets = useSafeAreaInsets();
  const respond = useRespond(invitation.id);
  const [busy, setBusy] = useState(false);
  const {event, host} = invitation;
  const today = todayInBerlin();

  const answer = async (status: InviteeStatus) => {
    setBusy(true);
    await respond(status);
    setBusy(false);
  };

  return (
    <>
      <ScrollView
        contentContainerStyle={[
          styles.content,
          {paddingBottom: FOOTER_SPACE + insets.bottom},
        ]}
      >
        <View style={styles.host}>
          <Avatar
            initials={initialsOfName(host.firstName, host.lastName)}
            color={friendColor(host.id, theme.colors)}
            size={56}
          />
          <View style={styles.hostText}>
            <Text variant="bodyStrong" testID="received.from">
              {s.invitesYou(fullName(host))}
            </Text>
            <Text variant="meta" tone="muted">
              {formatNotificationTime(invitation.createdAt)}
            </Text>
          </View>
        </View>
        {invitation.message ? (
          <MessageBubble
            message={invitation.message}
            testID="received.message"
          />
        ) : null}
        <InvitationEventCard
          name={event.name}
          when={
            event.status === 'cancelled'
              ? strings.lists.cancelled
              : whenText(event, today)
          }
          meta={eventMetaText(event)}
          imageUrl={event.coverImage?.cardUrl ?? event.coverImage?.thumbUrl}
          imageLabel="Festfoto"
          onPress={() =>
            navigate({pathname: '/f/[id]', params: {id: event.id}})
          }
          testID="received.event"
        />
        {invitation.others.length > 0 ? (
          <View style={styles.group}>
            <Text variant="label">{s.alsoInvited}</Text>
            {invitation.others.map(other => (
              <InviteeRow
                key={other.person.id}
                name={fullName(other.person)}
                initials={initialsOfName(
                  other.person.firstName,
                  other.person.lastName,
                )}
                color={friendColor(other.person.id, theme.colors)}
                status={other.status}
                testID={`received.other.${other.person.id}`}
              />
            ))}
          </View>
        ) : null}
      </ScrollView>
      <StickyFooter testID="received.footer">
        {invitation.status === 'open' ? (
          <>
            <Button
              label={s.decline}
              variant="secondary"
              onPress={() => void answer('declined')}
              disabled={busy}
              style={styles.decline}
              testID="received.decline"
            />
            <Button
              label={s.accept}
              onPress={() => void answer('accepted')}
              disabled={busy}
              style={styles.accept}
              testID="received.accept"
            />
          </>
        ) : (
          <ResponseBanner
            status={invitation.status}
            onChange={() => void answer('open')}
            disabled={busy}
            testID="received.banner"
          />
        )}
      </StickyFooter>
    </>
  );
}

const styles = StyleSheet.create({
  screen: {flex: 1},
  header: {
    flexDirection: 'row',
    alignItems: 'center',
    gap: 14,
    paddingHorizontal: 16,
    marginBottom: 16,
  },
  loading: {marginTop: 40},
  padded: {paddingHorizontal: 16, gap: 12},
  content: {paddingHorizontal: 16, gap: 18},
  host: {flexDirection: 'row', alignItems: 'center', gap: 14},
  hostText: {flex: 1, gap: 2},
  group: {gap: 14},
  decline: {flex: 1},
  accept: {flex: 1.4},
});
