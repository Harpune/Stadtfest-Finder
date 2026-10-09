import {useLocalSearchParams} from 'expo-router';

import {ListDetailScreen} from '@/features/lists/ListDetailScreen';

export default function ListRoute() {
  const {id} = useLocalSearchParams<{id: string}>();
  return <ListDetailScreen listId={id ?? ''} />;
}
