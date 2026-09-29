/** Start screen: "Entdecken" (R03) with map and list. */
import {Redirect} from 'expo-router';
import React from 'react';

import {DiscoverProvider} from '@/features/discover/DiscoverProvider';
import {DiscoverScreen} from '@/features/discover/DiscoverScreen';

const STORYBOOK_ENABLED = process.env.EXPO_PUBLIC_STORYBOOK_ENABLED === 'true';

export default function StartScreen() {
  if (STORYBOOK_ENABLED) {
    return <Redirect href="/storybook" />;
  }
  return (
    <DiscoverProvider>
      <DiscoverScreen />
    </DiscoverProvider>
  );
}
