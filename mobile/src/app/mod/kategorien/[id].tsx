/** Category form: `/mod/kategorien/neu` creates, `/mod/kategorien/{id}` edits (R09-US3). */
import {useLocalSearchParams} from 'expo-router';
import React from 'react';

import {CategoryFormScreen} from '@/features/moderation/categories/CategoryFormScreen';

export default function CategoryRoute() {
  const {id} = useLocalSearchParams<{id: string}>();
  return <CategoryFormScreen categoryId={id === 'neu' ? null : String(id)} />;
}
