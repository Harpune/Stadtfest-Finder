/**
 * State of the moderator's AI search (R10-US1/US2): start, poll every 10 s while it runs
 * (E-12), restore a running search when the moderation view opens again.
 */
import {useQueryClient} from '@tanstack/react-query';
import React, {
  createContext,
  PropsWithChildren,
  useCallback,
  useContext,
  useEffect,
  useMemo,
  useRef,
  useState,
} from 'react';

import {fetchClient} from '@/api/client';
import type {components} from '@/api/generated/schema';
import {useToast} from '@/components';
import {strings} from '@/strings/de';

import {MOD_EVENTS_QUERY} from '../useModeration';

export type AiSearch = components['schemas']['AiSearch'];
type ApiError = components['schemas']['Error'];

/** Polling interval while a search runs (E-12). */
export const POLL_MS = 10_000;

export type StartResult =
  {ok: true} | {ok: false; status: number; error?: ApiError};

interface AiSearchState {
  /** The search shown in the status bar, or null. */
  search: AiSearch | null;
  start: (postalCode: string) => Promise<StartResult>;
  /** Hides a finished search (✕, or after reviewing all finds). */
  dismiss: () => void;
}

const Context = createContext<AiSearchState | null>(null);

const active = (search: AiSearch | null) =>
  search?.status === 'queued' || search?.status === 'running';

export function AiSearchProvider({children}: PropsWithChildren) {
  const queryClient = useQueryClient();
  const toast = useToast();
  const [search, setSearch] = useState<AiSearch | null>(null);
  const searchRef = useRef(search);
  searchRef.current = search;

  // Restore a running search after "Beenden" or an app restart (R10-US2).
  useEffect(() => {
    let cancelled = false;
    void fetchClient
      .GET('/v1/mod/ai-searches', {params: {query: {status: 'running'}}})
      .then(({data}) => {
        if (!cancelled && data?.[0] && !searchRef.current) setSearch(data[0]);
      })
      .catch(() => undefined);
    return () => {
      cancelled = true;
    };
  }, []);

  const searchId = search?.id;
  const running = active(search);
  useEffect(() => {
    if (!searchId || !running) return undefined;
    const timer = setInterval(() => {
      void fetchClient
        .GET('/v1/mod/ai-searches/{jobId}', {params: {path: {jobId: searchId}}})
        .then(({data}) => {
          if (!data || data.status === 'queued' || data.status === 'running')
            return;
          setSearch(data);
          if (data.status === 'completed') {
            void queryClient.invalidateQueries({
              queryKey: MOD_EVENTS_QUERY.queryKey,
            });
            if (data.newEventIds.length > 0) {
              toast(strings.mod.ai.doneToast(data.newEventIds.length));
            }
          }
        })
        .catch(() => undefined);
    }, POLL_MS);
    return () => clearInterval(timer);
  }, [searchId, running, queryClient, toast]);

  const start = useCallback(
    async (postalCode: string): Promise<StartResult> => {
      const result = await fetchClient
        .POST('/v1/mod/ai-searches', {body: {postalCode}})
        .catch(() => undefined);
      if (result?.data) {
        setSearch(result.data);
        toast(strings.mod.ai.startedToast);
        return {ok: true};
      }
      const jobId = result?.error?.fields?.jobId;
      if (result?.response.status === 409 && jobId) {
        // Show the search that already runs instead.
        const running = await fetchClient
          .GET('/v1/mod/ai-searches/{jobId}', {params: {path: {jobId}}})
          .catch(() => undefined);
        if (running?.data) setSearch(running.data);
      }
      return {
        ok: false,
        status: result?.response.status ?? 0,
        error: result?.error,
      };
    },
    [toast],
  );

  const dismiss = useCallback(() => setSearch(null), []);

  const value = useMemo(
    () => ({search, start, dismiss}),
    [search, start, dismiss],
  );
  return <Context.Provider value={value}>{children}</Context.Provider>;
}

export function useAiSearch(): AiSearchState {
  const value = useContext(Context);
  if (!value) throw new Error('useAiSearch outside AiSearchProvider');
  return value;
}
