import {useLocalSearchParams} from 'expo-router';

import {HostInvitationScreen} from '@/features/invitations/HostInvitationScreen';

export default function HostInvitationRoute() {
  const {eventId} = useLocalSearchParams<{eventId: string}>();
  return <HostInvitationScreen eventId={eventId ?? ''} />;
}
