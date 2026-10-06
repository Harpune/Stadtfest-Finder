/**
 * Notification list and unread counter (R11-US1). The counter comes from the header
 * `X-Unread-Count`; it refreshes on app start, when a push arrives and after reading.
 */
import {
  InfiniteData,
  useInfiniteQuery,
  useQuery,
  useQueryClient,
} from '@tanstack/react-query';
import {useCallback} from 'react';

import {fetchClient} from '@/api/client';
import type {components} from '@/api/generated/schema';
import {useToast} from '@/components';
import {useAuth} from '@/features/auth/AuthProvider';
import {strings} from '@/strings/de';

export type AppNotification = components['schemas']['Notification'];
type NotificationPage = components['schemas']['NotificationPage'];
type Pages = InfiniteData<NotificationPage, string | undefined>;

export const PAGE_SIZE = 20;
/** All notification queries start with this key, so logout removes them (`/v1/me…`). */
export const NOTIFICATIONS_KEY = ['get', '/v1/me/notifications'] as const;
const LIST_KEY = [...NOTIFICATIONS_KEY, 'list'] as const;
export const UNREAD_KEY = [...NOTIFICATIONS_KEY, 'unread'] as const;

function unreadFrom(response: Response): number {
  const value = Number(response.headers.get('X-Unread-Count') ?? '0');
  return Number.isFinite(value) && value > 0 ? value : 0;
}

/** Pages of the caller's notifications, newest first. */
export function useNotificationList() {
  const {status} = useAuth();
  const queryClient = useQueryClient();
  return useInfiniteQuery({
    queryKey: LIST_KEY,
    enabled: status === 'signedIn',
    initialPageParam: undefined as string | undefined,
    getNextPageParam: (last: NotificationPage) => last.nextCursor ?? undefined,
    queryFn: async ({pageParam}) => {
      const {data, response} = await fetchClient.GET('/v1/me/notifications', {
        params: {query: {cursor: pageParam, limit: PAGE_SIZE}},
      });
      if (!data) throw new Error(`notifications ${response.status}`);
      queryClient.setQueryData(UNREAD_KEY, unreadFrom(response));
      return data;
    },
  });
}

/** Number of unread notifications (0 for guests). */
export function useUnreadCount(): number {
  const {status} = useAuth();
  const {data} = useQuery({
    queryKey: UNREAD_KEY,
    enabled: status === 'signedIn',
    queryFn: async () => {
      const {response} = await fetchClient.GET('/v1/me/notifications', {
        params: {query: {limit: 1}},
      });
      if (!response.ok) throw new Error(`unread ${response.status}`);
      return unreadFrom(response);
    },
  });
  return status === 'signedIn' ? (data ?? 0) : 0;
}

/** Reloads list and counter, e.g. when a push arrives. */
export function useRefreshNotifications() {
  const queryClient = useQueryClient();
  return useCallback(
    () => queryClient.invalidateQueries({queryKey: NOTIFICATIONS_KEY}),
    [queryClient],
  );
}

function markInPages(
  pages: Pages | undefined,
  id: string | null,
): Pages | undefined {
  if (!pages) return pages;
  return {
    ...pages,
    pages: pages.pages.map(page => ({
      ...page,
      items: page.items.map(item =>
        id === null || item.id === id ? {...item, read: true} : item,
      ),
    })),
  };
}

/**
 * Marks one notification (`id`) or all (`null`) as read, optimistically: dots and counter
 * disappear at once; on failure the previous state returns with a toast.
 */
export function useMarkRead() {
  const queryClient = useQueryClient();
  const toast = useToast();
  return useCallback(
    async (id: string | null, wasUnread = true) => {
      await queryClient.cancelQueries({queryKey: NOTIFICATIONS_KEY});
      const pages = queryClient.getQueryData<Pages>(LIST_KEY);
      const unread = queryClient.getQueryData<number>(UNREAD_KEY) ?? 0;
      queryClient.setQueryData(LIST_KEY, markInPages(pages, id));
      queryClient.setQueryData(
        UNREAD_KEY,
        id === null ? 0 : Math.max(unread - (wasUnread ? 1 : 0), 0),
      );
      const request =
        id === null
          ? fetchClient.POST('/v1/me/notifications/read-all')
          : fetchClient.POST('/v1/me/notifications/{notificationId}/read', {
              params: {path: {notificationId: id}},
            });
      const result = await request.catch(() => null);
      if (!result?.response.ok) {
        queryClient.setQueryData(LIST_KEY, pages);
        queryClient.setQueryData(UNREAD_KEY, unread);
        toast(strings.notifications.failed);
      }
    },
    [queryClient, toast],
  );
}
