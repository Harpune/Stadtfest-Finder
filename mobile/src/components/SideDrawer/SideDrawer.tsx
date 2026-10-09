import React, {
  PropsWithChildren,
  ReactNode,
  useEffect,
  useRef,
  useState,
} from 'react';
import {
  Animated,
  Easing,
  Modal,
  Pressable,
  ScrollView,
  StyleSheet,
  useWindowDimensions,
  View,
} from 'react-native';
import {useSafeAreaInsets} from 'react-native-safe-area-context';

import {strings} from '@/strings/de';
import {useTheme} from '@/theme';

/** Width of the visible map strip left of the drawer (design 03-07, 04-01). */
const MAP_STRIP = 54;

export interface SideDrawerProps {
  visible: boolean;
  onClose: () => void;
  testID: string;
  /** Fixed area at the bottom (e.g. "Abmelden"), separated by a line. */
  footer?: ReactNode;
  /**
   * False: the next close happens at once, without sliding out. Used when a drawer entry
   * opens another screen, so only that screen moves (no drawer-out, screen-in sequence).
   */
  animateClose?: boolean;
}

/**
 * Drawer sliding in from the right over a scrim (profile drawer). Tapping the scrim or the
 * Android back button closes it.
 */
export function SideDrawer({
  visible,
  onClose,
  testID,
  footer,
  animateClose = true,
  children,
}: PropsWithChildren<SideDrawerProps>) {
  const theme = useTheme();
  const c = theme.colors;
  const insets = useSafeAreaInsets();
  const {width} = useWindowDimensions();
  const panelWidth = width - MAP_STRIP;
  const [mounted, setMounted] = useState(visible);
  const progress = useRef(new Animated.Value(visible ? 1 : 0)).current;

  useEffect(() => {
    if (visible) setMounted(true);
    if (!visible && !animateClose) {
      progress.setValue(0);
      setMounted(false);
      return undefined;
    }
    const animation = Animated.timing(progress, {
      toValue: visible ? 1 : 0,
      duration: theme.motion.page.duration,
      easing: Easing.bezier(0.2, 0.8, 0.2, 1),
      useNativeDriver: true,
    });
    animation.start(({finished}) => {
      if (finished && !visible) setMounted(false);
    });
    return () => animation.stop();
  }, [visible, animateClose, progress, theme.motion.page.duration]);

  const panelStyle = {
    transform: [
      {
        translateX: progress.interpolate({
          inputRange: [0, 1],
          outputRange: [panelWidth, 0],
        }),
      },
    ],
  };
  const scrimStyle = {opacity: progress};

  if (!mounted && !visible) return null;

  return (
    <Modal
      visible
      transparent
      animationType="none"
      onRequestClose={onClose}
      statusBarTranslucent
    >
      <Animated.View
        style={[
          StyleSheet.absoluteFill,
          {backgroundColor: c.scrim},
          scrimStyle,
        ]}
      >
        <Pressable
          testID={`${testID}.scrim`}
          accessibilityRole="button"
          accessibilityLabel={strings.common.close}
          onPress={onClose}
          style={StyleSheet.absoluteFill}
        />
      </Animated.View>
      <Animated.View
        testID={testID}
        accessibilityViewIsModal
        style={[
          styles.panel,
          {
            width: panelWidth,
            backgroundColor: c.drawer,
            borderLeftColor: c.outline,
            paddingTop: insets.top + 12,
          },
          panelStyle,
        ]}
      >
        <ScrollView contentContainerStyle={styles.content}>
          {children}
        </ScrollView>
        {footer ? (
          <View
            style={[
              styles.footer,
              {
                borderTopColor: c.outline,
                paddingBottom: Math.max(insets.bottom, 16),
              },
            ]}
          >
            {footer}
          </View>
        ) : null}
      </Animated.View>
    </Modal>
  );
}

const styles = StyleSheet.create({
  panel: {
    position: 'absolute',
    top: 0,
    right: 0,
    bottom: 0,
    borderLeftWidth: 1,
  },
  content: {paddingHorizontal: 20, paddingBottom: 24, gap: 16},
  footer: {borderTopWidth: 1, paddingHorizontal: 20, paddingTop: 12},
});
