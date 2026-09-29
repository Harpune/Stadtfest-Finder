import React, {
  createContext,
  PropsWithChildren,
  useContext,
  useMemo,
  useReducer,
} from 'react';

import {
  DiscoverAction,
  discoverReducer,
  DiscoverState,
  INITIAL_DISCOVER_STATE,
} from './state';

interface DiscoverContextValue {
  state: DiscoverState;
  dispatch: React.Dispatch<DiscoverAction>;
}

const DiscoverContext = createContext<DiscoverContextValue | null>(null);

/** Holds the discover state for map and list (React context + reducer, no store library). */
export function DiscoverProvider({
  children,
  initialState = INITIAL_DISCOVER_STATE,
}: PropsWithChildren<{initialState?: DiscoverState}>) {
  const [state, dispatch] = useReducer(discoverReducer, initialState);
  const value = useMemo(() => ({state, dispatch}), [state]);
  return (
    <DiscoverContext.Provider value={value}>
      {children}
    </DiscoverContext.Provider>
  );
}

export function useDiscover(): DiscoverContextValue {
  const value = useContext(DiscoverContext);
  if (!value) {
    throw new Error('useDiscover must be used inside <DiscoverProvider>');
  }
  return value;
}
