/** Review of an AI search's finds (R10-US4, 09-04/09-05). */
import {useLocalSearchParams} from 'expo-router';
import React from 'react';

import {ReviewScreen} from '@/features/moderation/ai/ReviewScreen';

export default function ReviewRoute() {
  const {jobId} = useLocalSearchParams<{jobId: string}>();
  return <ReviewScreen jobId={String(jobId)} />;
}
