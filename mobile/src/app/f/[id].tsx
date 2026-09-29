/** Event detail route: /f/{id}, also reached via stadtfest://f/{id} and App Links (R04-US6). */
import {useLocalSearchParams} from 'expo-router';
import React from 'react';

import {EventDetailScreen} from '@/features/event-detail/EventDetailScreen';

export default function EventDetailRoute() {
  const {id} = useLocalSearchParams<{id: string}>();
  return <EventDetailScreen eventId={String(id)} />;
}
