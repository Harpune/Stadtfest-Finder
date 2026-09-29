/**
 * API access for the app: typed fetch client + TanStack Query hooks generated from
 * api/openapi.yaml (ADR 0008). Features use `$api` - never raw fetch.
 */
import {QueryClient} from '@tanstack/react-query';
import createFetchClient from 'openapi-fetch';
import createClient from 'openapi-react-query';

import type {paths} from './generated/schema';

/** Base URL of the backend, e.g. http://192.168.0.10:8000 for a device on the LAN. */
export const API_BASE_URL =
  process.env.EXPO_PUBLIC_API_URL ?? 'http://localhost:8000';

export const fetchClient = createFetchClient<paths>({
  baseUrl: API_BASE_URL,
  // The spec uses `style: form, explode: false` for arrays: `bbox=1,2,3,4`.
  querySerializer: {array: {style: 'form', explode: false}},
  // Resolve fetch per call (not at import) so tests can replace it.
  fetch: request => globalThis.fetch(request),
});

/** Typed TanStack Query hooks, e.g. `$api.useQuery('get', '/v1/health/live')`. */
export const $api = createClient(fetchClient);

export function createQueryClient(): QueryClient {
  return new QueryClient({
    defaultOptions: {
      queries: {retry: 1, staleTime: 30_000},
    },
  });
}
