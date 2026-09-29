/**
 * Auth state of the app. Until R05 the user is always a guest; account actions of guests
 * are remembered as `pendingAction` and shown in the guest hint sheet (R04-US5). After the
 * login (R05) the pending action is executed.
 */
import React, {
  createContext,
  PropsWithChildren,
  useCallback,
  useContext,
  useMemo,
  useState,
} from 'react';

import {GuestHintKind, GuestHintSheet, useToast} from '@/components';
import {strings} from '@/strings/de';

export interface PendingAction {
  type: GuestHintKind;
  eventId: string;
}

interface AuthContextValue {
  /** Signed-in user; always null until R05. */
  user: null;
  pendingAction: PendingAction | null;
  /**
   * Requests an account action. For guests it remembers the action and shows the hint.
   * Returns true if the caller may perform the action right away (signed in).
   */
  requestAccountAction: (action: PendingAction) => boolean;
}

const AuthContext = createContext<AuthContextValue | null>(null);

export function AuthProvider({children}: PropsWithChildren) {
  const toast = useToast();
  const [pendingAction, setPendingAction] = useState<PendingAction | null>(
    null,
  );
  const [hintVisible, setHintVisible] = useState(false);

  const requestAccountAction = useCallback((action: PendingAction) => {
    setPendingAction(action);
    setHintVisible(true);
    return false;
  }, []);

  const dismiss = useCallback(() => {
    setHintVisible(false);
    setPendingAction(null);
  }, []);

  const login = useCallback(() => {
    // Login follows in R05; the pending action is kept so R05 can execute it.
    setHintVisible(false);
    toast(strings.guestHint.loginSoon);
  }, [toast]);

  const value = useMemo(
    () => ({user: null, pendingAction, requestAccountAction}),
    [pendingAction, requestAccountAction],
  );

  return (
    <AuthContext.Provider value={value}>
      {children}
      <GuestHintSheet
        visible={hintVisible}
        kind={pendingAction?.type ?? 'favorite'}
        onLogin={login}
        onDismiss={dismiss}
      />
    </AuthContext.Provider>
  );
}

export function useAuth(): AuthContextValue {
  const value = useContext(AuthContext);
  if (!value) throw new Error('useAuth must be used inside <AuthProvider>');
  return value;
}
