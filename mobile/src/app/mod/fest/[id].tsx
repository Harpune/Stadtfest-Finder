/** Moderation form: `/mod/fest/neu` creates, `/mod/fest/{id}` edits an event (R07-US3). */
import {useLocalSearchParams} from 'expo-router';
import React from 'react';

import {ModEventFormScreen} from '@/features/moderation/ModEventFormScreen';

export default function ModEventRoute() {
  const {id} = useLocalSearchParams<{id: string}>();
  return <ModEventFormScreen eventId={id === 'neu' ? null : String(id)} />;
}
