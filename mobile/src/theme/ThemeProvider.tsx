/**
 * Provides the active theme. Default follows the system setting; a per-device override
 * (set from the profile drawer in R06) is persisted locally.
 */
import AsyncStorage from '@react-native-async-storage/async-storage';
import React, {
  createContext,
  PropsWithChildren,
  useCallback,
  useContext,
  useEffect,
  useMemo,
  useState,
} from 'react';
import {useColorScheme} from 'react-native';

import {ColorScheme, Theme, themes} from './theme';

export type ThemePreference = ColorScheme | 'system';

const STORAGE_KEY = 'theme-preference';

interface ThemeContextValue {
  theme: Theme;
  preference: ThemePreference;
  setPreference: (preference: ThemePreference) => void;
}

const ThemeContext = createContext<ThemeContextValue | null>(null);

interface ThemeProviderProps {
  /** Forces a scheme (tests, Storybook). Overrides system and stored preference. */
  forcedScheme?: ColorScheme;
}

export function ThemeProvider({
  children,
  forcedScheme,
}: PropsWithChildren<ThemeProviderProps>) {
  const systemScheme = useColorScheme();
  const [preference, setPreferenceState] = useState<ThemePreference>('system');

  useEffect(() => {
    AsyncStorage.getItem(STORAGE_KEY)
      .then(stored => {
        if (stored === 'dark' || stored === 'light' || stored === 'system') {
          setPreferenceState(stored);
        }
      })
      .catch(() => undefined); // fall back to the system setting
  }, []);

  const setPreference = useCallback((next: ThemePreference) => {
    setPreferenceState(next);
    AsyncStorage.setItem(STORAGE_KEY, next).catch(() => undefined);
  }, []);

  const scheme: ColorScheme =
    forcedScheme ??
    (preference === 'system'
      ? systemScheme === 'light'
        ? 'light'
        : 'dark'
      : preference);

  const value = useMemo(
    () => ({theme: themes[scheme], preference, setPreference}),
    [scheme, preference, setPreference],
  );

  return (
    <ThemeContext.Provider value={value}>{children}</ThemeContext.Provider>
  );
}

function useThemeContext(): ThemeContextValue {
  const context = useContext(ThemeContext);
  if (!context) {
    throw new Error('useTheme must be used inside <ThemeProvider>');
  }
  return context;
}

/** Returns the active theme. */
export function useTheme(): Theme {
  return useThemeContext().theme;
}

/** Returns the theme preference and a setter (for the dark-mode switch). */
export function useThemePreference(): Pick<
  ThemeContextValue,
  'preference' | 'setPreference'
> {
  const {preference, setPreference} = useThemeContext();
  return {preference, setPreference};
}
