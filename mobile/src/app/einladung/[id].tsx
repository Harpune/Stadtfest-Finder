import {useLocalSearchParams} from 'expo-router';

import {ReceivedInvitationScreen} from '@/features/invitations/ReceivedInvitationScreen';

export default function ReceivedInvitationRoute() {
  const {id} = useLocalSearchParams<{id: string}>();
  return <ReceivedInvitationScreen invitationId={id ?? ''} />;
}
