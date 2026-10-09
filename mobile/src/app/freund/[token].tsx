import {useLocalSearchParams} from 'expo-router';

import {AcceptFriendScreen} from '@/features/friends/AcceptFriendScreen';

export default function FriendLinkRoute() {
  const {token} = useLocalSearchParams<{token: string}>();
  return <AcceptFriendScreen token={token ?? ''} />;
}
