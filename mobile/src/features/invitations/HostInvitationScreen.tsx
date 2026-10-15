/**
 * The own invitation to an event (R14-US2, US4): the overview with counters, message and
 * groups (06-01), or "Freunde einladen" (06-02) while nobody was invited yet and after
 * "Weitere einladen".
 */
import {router} from 'expo-router';
import React, {useState} from 'react';
import {
  ActivityIndicator,
  Platform,
  Pressable,
  ScrollView,
  Share,
  StyleSheet,
  View,
} from 'react-native';
import {useSafeAreaInsets} from 'react-native-safe-area-context';

import {
  Avatar,
  Button,
  CheckRow,
  EventHeaderCard,
  Icon,
  IconButton,
  InvitationCounts,
  InviteeRow,
  MessageBubble,
  StickyFooter,
  Text,
  TextField,
} from '@/components';
import {initialsOf, useAuth} from '@/features/auth/AuthProvider';
import {
  displayName,
  friendColor,
  initialsOfName,
} from '@/features/friends/friends';
import {useFriends} from '@/features/friends/useFriends';
import {navigate} from '@/features/navigation/navigate';
import {strings} from '@/strings/de';
import {useTheme} from '@/theme';

import {
  eventMetaText,
  fullName,
  groupInvitees,
  invitationLinkUrl,
  inviteeMeta,
} from './format';
import {
  HostInvitation,
  Invitee,
  useHostActions,
  useHostInvitation,
} from './useInvitations';

const s = strings.invitations;
const MESSAGE_MAX = 280;
const FOOTER_SPACE = 110;

type EventInfo = HostInvitation['event'];

export function HostInvitationScreen({
  eventId,
  event,
}: {
  eventId: string;
  /** Event data known from the detail page, shown before anything is loaded. */
  event?: EventInfo;
}) {
  const theme = useTheme();
  const insets = useSafeAreaInsets();
  const invitation = useHostInvitation(eventId);
  const [composing, setComposing] = useState(false);

  const back = () => {
    if (composing && invitation.data) {
      setComposing(false);
      return;
    }
    if (router.canGoBack()) router.back();
    else router.replace('/');
  };

  const showCompose = composing || invitation.data === null;
  let content: React.ReactNode;
  if (invitation.isPending) {
    content = (
      <ActivityIndicator style={styles.loading} testID="invitation.loading" />
    );
  } else if (invitation.isError) {
    content = (
      <View style={styles.padded} testID="invitation.error">
        <Text variant="displayS">{s.failed}</Text>
        <Button
          label={strings.common.retry}
          variant="secondary"
          onPress={() => void invitation.refetch()}
          testID="invitation.retry"
        />
      </View>
    );
  } else if (showCompose) {
    content = (
      <Compose
        eventId={eventId}
        event={invitation.data?.event ?? event}
        invited={invitation.data?.invitees ?? []}
        onSent={() => setComposing(false)}
      />
    );
  } else if (invitation.data) {
    content = (
      <Overview
        eventId={eventId}
        invitation={invitation.data}
        onInviteMore={() => setComposing(true)}
      />
    );
  }

  return (
    <View
      style={[
        styles.screen,
        {backgroundColor: theme.colors.background, paddingTop: insets.top + 8},
      ]}
      testID="invitation.screen"
    >
      <View style={styles.header}>
        <IconButton
          icon={<Icon name="chevronLeft" size={22} />}
          accessibilityLabel={strings.detail.back}
          onPress={back}
          variant="surface"
          testID="invitation.back"
        />
        <Text variant="displayL" style={styles.title} numberOfLines={1}>
          {showCompose ? s.composeTitle : s.overviewTitle}
        </Text>
      </View>
      {content}
    </View>
  );
}

function EventHead({eventId, event}: {eventId: string; event?: EventInfo}) {
  if (!event) return null;
  return (
    <EventHeaderCard
      name={event.name}
      meta={eventMetaText(event)}
      imageUrl={event.coverImage?.thumbUrl}
      onPress={() => navigate({pathname: '/f/[id]', params: {id: eventId}})}
      testID="invitation.event"
    />
  );
}

function Overview({
  eventId,
  invitation,
  onInviteMore,
}: {
  eventId: string;
  invitation: HostInvitation;
  onInviteMore: () => void;
}) {
  const theme = useTheme();
  const insets = useSafeAreaInsets();
  const {user} = useAuth();
  const {remind} = useHostActions(eventId);
  const [reminding, setReminding] = useState(false);
  const groups = groupInvitees(invitation.invitees);

  const row = (invitee: Invitee) => (
    <InviteeRow
      key={invitee.person.id}
      name={fullName(invitee.person)}
      initials={initialsOfName(
        invitee.person.firstName,
        invitee.person.lastName,
      )}
      color={friendColor(invitee.person.id, theme.colors)}
      meta={inviteeMeta(invitee)}
      status={invitee.status}
      testID={`invitation.invitee.${invitee.person.id}`}
    />
  );

  const onRemind = async () => {
    setReminding(true);
    await remind(invitation);
    setReminding(false);
  };

  return (
    <>
      <ScrollView
        contentContainerStyle={[
          styles.content,
          {paddingBottom: FOOTER_SPACE + insets.bottom},
        ]}
      >
        <EventHead eventId={eventId} event={invitation.event} />
        <InvitationCounts
          coming={groups.accepted.length + 1}
          open={groups.open.length}
          declined={groups.declined.length}
          testID="invitation.counts"
        />
        {invitation.message ? (
          <MessageBubble
            message={invitation.message}
            testID="invitation.message"
          />
        ) : null}

        <Group title={s.groupComing}>
          <InviteeRow
            name={s.you}
            initials={initialsOf(user)}
            meta={s.host}
            status="accepted"
            testID="invitation.host"
          />
          {groups.accepted.map(row)}
        </Group>
        {groups.open.length > 0 ? (
          <Group title={s.groupOpen}>{groups.open.map(row)}</Group>
        ) : null}
        {groups.declined.length > 0 ? (
          <Group title={s.groupDeclined}>{groups.declined.map(row)}</Group>
        ) : null}
      </ScrollView>
      <StickyFooter testID="invitation.footer">
        <Button
          label={s.remind}
          variant="secondary"
          onPress={() => void onRemind()}
          loading={reminding}
          testID="invitation.remind"
        />
        <Button
          label={s.inviteMore}
          onPress={onInviteMore}
          style={styles.flex}
          testID="invitation.more"
        />
      </StickyFooter>
    </>
  );
}

function Compose({
  eventId,
  event,
  invited,
  onSent,
}: {
  eventId: string;
  event?: EventInfo;
  invited: Invitee[];
  onSent: () => void;
}) {
  const theme = useTheme();
  const insets = useSafeAreaInsets();
  const friends = useFriends();
  const {invite, linkToken} = useHostActions(eventId);
  const [selected, setSelected] = useState<string[]>([]);
  const [message, setMessage] = useState('');
  const [sending, setSending] = useState(false);

  // Already invited friends are hidden (06-02).
  const invitedIds = new Set(invited.map(i => i.person.id));
  const candidates = (friends.data?.items ?? []).filter(
    friend => !invitedIds.has(friend.id),
  );

  const toggle = (id: string) =>
    setSelected(current =>
      current.includes(id) ? current.filter(x => x !== id) : [...current, id],
    );

  const send = async () => {
    setSending(true);
    const ok = await invite(selected, message);
    setSending(false);
    if (ok) {
      setSelected([]);
      setMessage('');
      onSent();
    }
  };

  const shareLink = async () => {
    const token = await linkToken();
    if (!token) return;
    const url = invitationLinkUrl(token);
    const text = s.shareLinkMessage(event?.name ?? '', url);
    try {
      await Share.share(
        Platform.OS === 'ios' ? {message: text, url} : {message: text},
      );
    } catch {
      // Sheet closed or no share target; nothing to report.
    }
  };

  let list: React.ReactNode;
  if (friends.isPending) {
    list = <ActivityIndicator testID="invitation.compose.loading" />;
  } else if (candidates.length === 0) {
    list = (
      <Text variant="body" tone="muted" testID="invitation.compose.empty">
        {invited.length > 0 ? s.allInvited : s.noFriends}
      </Text>
    );
  } else {
    list = (
      <View
        style={[
          styles.card,
          {
            backgroundColor: theme.colors.surface,
            borderRadius: theme.radius.block,
          },
        ]}
      >
        {candidates.map(friend => (
          <CheckRow
            key={friend.id}
            label={displayName(friend.firstName, friend.lastName)}
            lead={
              <Avatar
                initials={initialsOfName(friend.firstName, friend.lastName)}
                color={friendColor(friend.id, theme.colors)}
                size={40}
              />
            }
            checked={selected.includes(friend.id)}
            onPress={() => toggle(friend.id)}
            testID={`invitation.friend.${friend.id}`}
          />
        ))}
      </View>
    );
  }

  return (
    <>
      <ScrollView
        keyboardShouldPersistTaps="handled"
        contentContainerStyle={[
          styles.content,
          {paddingBottom: FOOTER_SPACE + insets.bottom},
        ]}
      >
        <EventHead eventId={eventId} event={event} />
        <Text variant="label">{s.whom}</Text>
        {list}
        <TextField
          label={s.messagePlaceholder}
          hideLabel
          placeholder={s.messagePlaceholder}
          value={message}
          onChangeText={setMessage}
          maxLength={MESSAGE_MAX}
          multiline
          testID="invitation.compose.message"
        />
        <Pressable
          accessibilityRole="button"
          onPress={() => void shareLink()}
          hitSlop={8}
          testID="invitation.compose.shareLink"
        >
          <Text variant="bodyStrong" tone="primary">
            {s.shareLink}
          </Text>
        </Pressable>
      </ScrollView>
      <StickyFooter testID="invitation.compose.footer">
        <Button
          label={s.send(selected.length)}
          onPress={() => void send()}
          disabled={selected.length === 0}
          loading={sending}
          style={styles.flex}
          testID="invitation.compose.send"
        />
      </StickyFooter>
    </>
  );
}

function Group({title, children}: React.PropsWithChildren<{title: string}>) {
  return (
    <View style={styles.group}>
      <Text variant="label">{title}</Text>
      {children}
    </View>
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
  title: {flex: 1},
  loading: {marginTop: 40},
  padded: {paddingHorizontal: 16, gap: 12},
  content: {paddingHorizontal: 16, gap: 18},
  card: {paddingHorizontal: 12},
  group: {gap: 14},
  flex: {flex: 1},
});
