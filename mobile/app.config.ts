/**
 * Dynamic Expo config on top of app.json. The link domain for App Links (and later iOS
 * Universal Links) comes from EXPO_PUBLIC_LINK_HOST at build time (R04-US6); the same
 * variable builds share links in the app (features/event-detail/links.ts).
 */
import type {ConfigContext, ExpoConfig} from 'expo/config';

const LINK_HOST =
  process.env.EXPO_PUBLIC_LINK_HOST || 'stadtfest.herderstreet.de';

export default ({config}: ConfigContext): ExpoConfig => ({
  ...(config as ExpoConfig),
  android: {
    ...config.android,
    intentFilters: [
      {
        action: 'VIEW',
        autoVerify: true,
        data: [
          {scheme: 'https', host: LINK_HOST, pathPrefix: '/f/'},
          // Friend links (R12).
          {scheme: 'https', host: LINK_HOST, pathPrefix: '/freund/'},
        ],
        category: ['BROWSABLE', 'DEFAULT'],
      },
    ],
  },
});
