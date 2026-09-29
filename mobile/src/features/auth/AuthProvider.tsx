/**
 * Auth state of the app (flow B, R05). Guests keep full access to map, list and details;
 * account actions of guests are remembered as `pendingAction`, shown in the guest hint
 * sheet (R04-US5) and executed after the login.
 */
import {useQueryClient} from '@tanstack/react-query';
import {router} from 'expo-router';
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

import {$api, fetchClient} from '@/api/client';
import type {components} from '@/api/generated/schema';
import {GuestHintKind, GuestHintSheet, useToast} from '@/components';
import {strings} from '@/strings/de';

import {authSession} from './authSession';
import type {LoginMethod} from './config';
import {loginWithIdp, LoginResult, revokeRefreshToken} from './oidc';
import type {Session} from './session';
import {readIdTokenClaims} from './tokens';

export type Me = components['schemas']['Me'];

export interface PendingAction {
  type: GuestHintKind;
  eventId: string;
}

export type AuthStatus = 'restoring' | 'guest' | 'signedIn';

/** IdP operations; replaced by fakes in tests. */
export interface AuthGateway {
  session: Session;
  login: (method: LoginMethod) => Promise<LoginResult>;
  revoke: (refreshToken: string) => Promise<void>;
}

const defaultGateway: AuthGateway = {
  session: authSession,
  login: loginWithIdp,
  revoke: revokeRefreshToken,
};

interface AuthContextValue {
  status: AuthStatus;
  /** Profile from `GET /v1/me`; null for guests (or while offline after a restart). */
  user: Me | null;
  /** Email from the ID token; the backend never stores it (E-08). */
  email: string | null;
  isModerator: boolean;
  pendingAction: PendingAction | null;
  /**
   * Requests an account action. For guests it remembers the action and shows the hint.
   * Returns true if the caller may perform the action right away (signed in).
   */
  requestAccountAction: (action: PendingAction) => boolean;
  /** Opens the login entry screen. */
  openLogin: () => void;
  /** Runs the login; resolves with the outcome so the entry screen can close itself. */
  login: (method: LoginMethod) => Promise<LoginResult['type']>;
  logout: () => Promise<void>;
  deleteAccount: () => Promise<boolean>;
  updateName: (firstName: string, lastName: string) => Promise<boolean>;
}

const AuthContext = createContext<AuthContextValue | null>(null);

const ME_QUERY = $api.queryOptions('get', '/v1/me');

/** Query keys of user-specific data; all such paths start with `/v1/me`. */
function isUserQuery(queryKey: readonly unknown[]): boolean {
  return typeof queryKey[1] === 'string' && queryKey[1].startsWith('/v1/me');
}

export function AuthProvider({
  children,
  gateway = defaultGateway,
}: PropsWithChildren<{gateway?: AuthGateway}>) {
  const toast = useToast();
  const queryClient = useQueryClient();
  const {session} = gateway;
  const [status, setStatus] = useState<AuthStatus>('restoring');
  const [user, setUser] = useState<Me | null>(null);
  const [idToken, setIdToken] = useState<string | null>(null);
  const [pendingAction, setPendingAction] = useState<PendingAction | null>(
    null,
  );
  const [hintVisible, setHintVisible] = useState(false);
  const pendingRef = useRef<PendingAction | null>(null);
  pendingRef.current = pendingAction;

  const resetToGuest = useCallback(() => {
    setStatus('guest');
    setUser(null);
    setIdToken(null);
    queryClient.removeQueries({predicate: q => isUserQuery(q.queryKey)});
  }, [queryClient]);

  const loadProfile = useCallback(async (): Promise<Me | null> => {
    try {
      const me = await queryClient.fetchQuery({...ME_QUERY, staleTime: 0});
      setUser(me);
      return me;
    } catch {
      return null; // offline or expired; expiry is handled by the session listener
    }
  }, [queryClient]);

  // App start: restore the session from secure storage.
  useEffect(() => {
    let active = true;
    session
      .restore()
      .then(async restored => {
        if (!active) return;
        if (!restored) {
          setStatus('guest');
          return;
        }
        setIdToken(session.current?.idToken ?? null);
        setStatus('signedIn');
        await loadProfile();
      })
      .catch(() => active && setStatus('guest'));
    return () => {
      active = false;
    };
  }, [session, loadProfile]);

  // Renewal rejected: back to guest mode (R05-US4).
  useEffect(
    () =>
      session.onExpired(() => {
        resetToGuest();
        toast(strings.login.sessionExpired);
      }),
    [session, resetToGuest, toast],
  );

  const executePendingAction = useCallback(
    (me: Me | null) => {
      const action = pendingRef.current;
      setPendingAction(null);
      switch (action?.type) {
        case 'favorite':
          // R06 sets the favorite here (PUT /v1/me/favorites/{id}).
          toast(strings.login.favoriteSaved);
          return;
        case 'invite':
          // R14 reopens the invitation here.
          router.push({pathname: '/f/[id]', params: {id: action.eventId}});
          return;
        default:
          toast(strings.login.welcome(me?.firstName ?? ''));
      }
    },
    [toast],
  );

  const login = useCallback(
    async (method: LoginMethod) => {
      const result = await gateway.login(method);
      if (result.type === 'error') {
        toast(strings.login.failed);
      }
      if (result.type !== 'success') return result.type;
      await session.start(result.tokens);
      setIdToken(result.tokens.idToken);
      setStatus('signedIn');
      const me = await loadProfile();
      executePendingAction(me);
      return result.type;
    },
    [gateway, session, toast, loadProfile, executePendingAction],
  );

  const endSession = useCallback(async () => {
    await session.end();
    resetToGuest();
    if (router.canDismiss()) router.dismissAll();
  }, [session, resetToGuest]);

  const logout = useCallback(async () => {
    const refreshToken = session.current?.refreshToken;
    // R11: DELETE /v1/me/devices/{token} before revoking.
    if (refreshToken) await gateway.revoke(refreshToken);
    await endSession();
    toast(strings.login.loggedOut);
  }, [gateway, session, endSession, toast]);

  const deleteAccount = useCallback(async () => {
    const {response} = await fetchClient.DELETE('/v1/me').catch(() => ({
      response: null,
    }));
    if (response?.status !== 204) {
      toast(strings.account.deleteFailed);
      return false;
    }
    await endSession();
    toast(strings.account.deleted);
    return true;
  }, [endSession, toast]);

  const updateName = useCallback(
    async (firstName: string, lastName: string) => {
      const {data} = await fetchClient
        .PATCH('/v1/me', {body: {firstName, lastName}})
        .catch(() => ({data: undefined}));
      if (!data) {
        toast(strings.name.saveFailed);
        return false;
      }
      setUser(data);
      queryClient.setQueryData(ME_QUERY.queryKey, data);
      return true;
    },
    [queryClient, toast],
  );

  const openLogin = useCallback(() => {
    setHintVisible(false);
    router.push('/login');
  }, []);

  const requestAccountAction = useCallback(
    (action: PendingAction) => {
      if (status === 'signedIn') return true;
      setPendingAction(action);
      setHintVisible(true);
      return false;
    },
    [status],
  );

  const dismissHint = useCallback(() => {
    setHintVisible(false);
    setPendingAction(null);
  }, []);

  const value = useMemo<AuthContextValue>(
    () => ({
      status,
      user,
      email: readIdTokenClaims(idToken).email ?? null,
      isModerator: user?.roles.includes('moderator') ?? false,
      pendingAction,
      requestAccountAction,
      openLogin,
      login,
      logout,
      deleteAccount,
      updateName,
    }),
    [
      status,
      user,
      idToken,
      pendingAction,
      requestAccountAction,
      openLogin,
      login,
      logout,
      deleteAccount,
      updateName,
    ],
  );

  return (
    <AuthContext.Provider value={value}>
      {children}
      <GuestHintSheet
        visible={hintVisible}
        kind={pendingAction?.type ?? 'favorite'}
        onLogin={openLogin}
        onDismiss={dismissHint}
      />
    </AuthContext.Provider>
  );
}

export function useAuth(): AuthContextValue {
  const value = useContext(AuthContext);
  if (!value) throw new Error('useAuth must be used inside <AuthProvider>');
  return value;
}

/** Initials for the avatar, e.g. "LH"; empty if no name is known. */
export function initialsOf(user: Pick<Me, 'firstName' | 'lastName'> | null) {
  if (!user) return '';
  return `${user.firstName.charAt(0)}${user.lastName.charAt(0)}`.toUpperCase();
}
