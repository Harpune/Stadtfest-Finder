import React, {
  createContext,
  PropsWithChildren,
  useCallback,
  useContext,
  useEffect,
  useRef,
  useState,
} from 'react';
import {Animated, Pressable, StyleSheet, View} from 'react-native';
import {useSafeAreaInsets} from 'react-native-safe-area-context';

import {themes, useTheme} from '@/theme';

import {Text} from '../Text/Text';

export interface ToastOptions {
  /** Optional action, e.g. "Erneut versuchen". */
  action?: {label: string; onPress: () => void};
}

interface ToastState extends ToastOptions {
  id: number;
  message: string;
}

type ShowToast = (message: string, options?: ToastOptions) => void;

const ToastContext = createContext<ShowToast | null>(null);

/** Hosts toasts at the bottom of the screen. One toast at a time; a new one replaces the old. */
export function ToastProvider({children}: PropsWithChildren) {
  const [toast, setToast] = useState<ToastState | null>(null);
  const nextId = useRef(0);

  const show = useCallback<ShowToast>((message, options) => {
    nextId.current += 1;
    setToast({id: nextId.current, message, ...options});
  }, []);

  return (
    <ToastContext.Provider value={show}>
      {children}
      {toast ? (
        <ToastView
          key={toast.id}
          toast={toast}
          onHidden={() => setToast(null)}
        />
      ) : null}
    </ToastContext.Provider>
  );
}

/** Returns a function that shows a toast (visible 2.2 s). */
export function useToast(): ShowToast {
  const show = useContext(ToastContext);
  if (!show) {
    throw new Error('useToast must be used inside <ToastProvider>');
  }
  return show;
}

interface ToastViewProps {
  toast: ToastState;
  onHidden: () => void;
}

export function ToastView({toast, onHidden}: ToastViewProps) {
  const theme = useTheme();
  const insets = useSafeAreaInsets();
  const progress = useRef(new Animated.Value(0)).current;
  const {duration, visible} = theme.motion.toast;
  const onHiddenRef = useRef(onHidden);
  onHiddenRef.current = onHidden;

  useEffect(() => {
    const animation = Animated.sequence([
      Animated.timing(progress, {toValue: 1, duration, useNativeDriver: true}),
      Animated.delay(visible),
      Animated.timing(progress, {toValue: 0, duration, useNativeDriver: true}),
    ]);
    animation.start(({finished}) => {
      if (finished) onHiddenRef.current();
    });
    return () => animation.stop();
  }, [progress, duration, visible]);

  const inverted = themes[theme.scheme === 'dark' ? 'light' : 'dark'];
  const actionColor = inverted.colors.primaryText;
  const translateY = progress.interpolate({
    inputRange: [0, 1],
    outputRange: [12, 0],
  });

  return (
    <View
      pointerEvents="box-none"
      style={[styles.host, {bottom: insets.bottom + 24}]}
    >
      <Animated.View
        testID="toast"
        accessibilityRole="alert"
        accessibilityLiveRegion="polite"
        style={[
          styles.toast,
          theme.shadow.toast,
          {
            // Inverted surface: light toast in dark mode and vice versa.
            backgroundColor: theme.colors.onSurface,
            borderRadius: theme.radius.button,
            opacity: progress,
            transform: [{translateY}],
          },
        ]}
      >
        <Text
          variant="bodyStrong"
          style={{color: theme.colors.background, flexShrink: 1}}
        >
          {toast.message}
        </Text>
        {toast.action ? (
          <Pressable
            testID="toast.action"
            accessibilityRole="button"
            onPress={toast.action.onPress}
            hitSlop={12}
          >
            <Text variant="bodyStrong" style={{color: actionColor}}>
              {toast.action.label}
            </Text>
          </Pressable>
        ) : null}
      </Animated.View>
    </View>
  );
}

const styles = StyleSheet.create({
  host: {position: 'absolute', left: 16, right: 16, alignItems: 'center'},
  toast: {
    flexDirection: 'row',
    alignItems: 'center',
    gap: 16,
    paddingHorizontal: 18,
    paddingVertical: 14,
    maxWidth: 420,
  },
});
