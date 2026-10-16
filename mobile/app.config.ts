/**
 * Dynamic Expo config on top of app.json. The link domain for App Links and iOS Universal
 * Links comes from EXPO_PUBLIC_LINK_HOST at build time (R04-US6); the same variable builds
 * share links in the app (features/event-detail/links.ts). The server side (assetlinks.json,
 * apple-app-site-association) is rendered by Caddy from the stack environment (R16).
 */
import type {ConfigContext, ExpoConfig} from 'expo/config';

const LINK_HOST =
  process.env.EXPO_PUBLIC_LINK_HOST || 'stadtfest.herderstreet.de';

export default ({config}: ConfigContext): ExpoConfig => ({
  ...(config as ExpoConfig),
  ios: {
    ...config.ios,
    associatedDomains: [`applinks:${LINK_HOST}`],
    // Only HTTPS through the OS: no export compliance question per TestFlight build (R16).
    config: {...config.ios?.config, usesNonExemptEncryption: false},
  },
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
          // Invitations (R14): invitation links and received invitations.
          {scheme: 'https', host: LINK_HOST, pathPrefix: '/e/'},
          {scheme: 'https', host: LINK_HOST, pathPrefix: '/einladung/'},
        ],
        category: ['BROWSABLE', 'DEFAULT'],
      },
    ],
  },
});
