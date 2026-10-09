import {useLocalSearchParams} from 'expo-router';

import {InvitationLinkScreen} from '@/features/invitations/InvitationLinkScreen';

export default function InvitationLinkRoute() {
  const {token} = useLocalSearchParams<{token: string}>();
  return <InvitationLinkScreen token={token ?? ''} />;
}
