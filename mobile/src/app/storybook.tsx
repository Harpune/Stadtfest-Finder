/**
 * Storybook route (development only). Reachable when the app is started with
 * `pnpm storybook`; otherwise it redirects to the start screen.
 */
import {Redirect} from 'expo-router';
import React from 'react';

const STORYBOOK_ENABLED = process.env.EXPO_PUBLIC_STORYBOOK_ENABLED === 'true';

export default function StorybookScreen() {
  if (!STORYBOOK_ENABLED) {
    return <Redirect href="/" />;
  }
  // Loaded lazily so that Storybook is not part of the regular app bundle.

  const StorybookUIRoot = require('../../.rnstorybook')
    .default as React.ComponentType;
  return <StorybookUIRoot />;
}
