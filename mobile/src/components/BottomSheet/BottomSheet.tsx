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
  View,
} from 'react-native';
import {useSafeAreaInsets} from 'react-native-safe-area-context';

import {strings} from '@/strings/de';
import {useTheme} from '@/theme';

import {IconButton} from '../IconButton/IconButton';
import {Icon} from '../Icon/Icon';
import {Text} from '../Text/Text';

export interface BottomSheetProps {
  visible: boolean;
  onClose: () => void;
  title: string;
  testID: string;
  /** Fixed footer below the scrollable content (e.g. primary action). */
  footer?: ReactNode;
}

/**
 * Bottom sheet (radius 28, handle 40 × 5, serif title, ✕). Slides in from below in 340 ms,
 * the scrim fades in 300 ms. Tapping the scrim, ✕ or Android back closes it.
 */
export function BottomSheet({
  visible,
  onClose,
  title,
  testID,
  footer,
  children,
}: PropsWithChildren<BottomSheetProps>) {
  const theme = useTheme();
  const insets = useSafeAreaInsets();
  const progress = useRef(new Animated.Value(0)).current;
  const [mounted, setMounted] = useState(visible);

  useEffect(() => {
    if (visible) setMounted(true);
    Animated.timing(progress, {
      toValue: visible ? 1 : 0,
      duration: theme.motion.sheet.duration,
      easing: Easing.bezier(0.2, 0.8, 0.2, 1),
      useNativeDriver: true,
    }).start(({finished}) => {
      if (finished && !visible) setMounted(false);
    });
  }, [visible, progress, theme.motion.sheet.duration]);

  if (!mounted) return null;

  const translateY = progress.interpolate({
    inputRange: [0, 1],
    outputRange: [800, 0],
  });
  const c = theme.colors;
  return (
    <Modal
      transparent
      visible
      animationType="none"
      onRequestClose={onClose}
      statusBarTranslucent
    >
      <Animated.View
        style={[
          StyleSheet.absoluteFill,
          {backgroundColor: c.scrim, opacity: progress},
        ]}
      >
        <Pressable
          testID={`${testID}.scrim`}
          accessibilityLabel={strings.common.close}
          style={StyleSheet.absoluteFill}
          onPress={onClose}
        />
      </Animated.View>
      <Animated.View
        testID={testID}
        accessibilityViewIsModal
        style={[
          styles.sheet,
          {
            backgroundColor: c.sheet,
            borderTopLeftRadius: theme.radius.sheet,
            borderTopRightRadius: theme.radius.sheet,
            transform: [{translateY}],
          },
        ]}
      >
        <View style={[styles.handle, {backgroundColor: c.outline}]} />
        <View style={styles.header}>
          <Text variant="displayL" accessibilityRole="header">
            {title}
          </Text>
          <IconButton
            icon={<Icon name="close" size={20} />}
            accessibilityLabel={strings.common.close}
            onPress={onClose}
            testID={`${testID}.close`}
            variant="surface"
            size={40}
          />
        </View>
        <ScrollView
          style={styles.body}
          contentContainerStyle={styles.bodyContent}
          keyboardShouldPersistTaps="handled"
        >
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
        ) : (
          <View style={{height: insets.bottom}} />
        )}
      </Animated.View>
    </Modal>
  );
}

const styles = StyleSheet.create({
  sheet: {position: 'absolute', left: 0, right: 0, bottom: 0, maxHeight: '88%'},
  handle: {
    alignSelf: 'center',
    width: 40,
    height: 5,
    borderRadius: 3,
    marginTop: 10,
  },
  header: {
    flexDirection: 'row',
    alignItems: 'center',
    justifyContent: 'space-between',
    paddingHorizontal: 20,
    paddingTop: 14,
    paddingBottom: 8,
  },
  body: {flexGrow: 0},
  bodyContent: {paddingHorizontal: 20, paddingBottom: 22, gap: 22},
  footer: {
    flexDirection: 'row',
    alignItems: 'center',
    gap: 16,
    paddingHorizontal: 20,
    paddingTop: 12,
    borderTopWidth: 1,
  },
});
