/**
 * Legal pages on the deep-link domain, served by the edge image (infra/edge/Caddyfile,
 * R16-US6). The host is the same as for shared links (EXPO_PUBLIC_LINK_HOST).
 */
import {LINK_HOST} from '@/features/event-detail/links';

export const LEGAL_URLS = {
  imprint: `https://${LINK_HOST}/impressum`,
  privacy: `https://${LINK_HOST}/datenschutz`,
  terms: `https://${LINK_HOST}/nutzungsbedingungen`,
} as const;
