import {
  BottomSheetBackdrop,
  type BottomSheetBackdropProps,
  BottomSheetFooter,
  type BottomSheetFooterProps,
  BottomSheetModal,
  BottomSheetScrollView,
} from '@gorhom/bottom-sheet';
import React, {
  PropsWithChildren,
  ReactNode,
  useCallback,
  useEffect,
  useRef,
  useState,
} from 'react';
import {StyleSheet, useWindowDimensions, View} from 'react-native';
import {useSafeAreaInsets} from 'react-native-safe-area-context';

import {strings} from '@/strings/de';
import {useTheme} from '@/theme';

import {IconButton} from '../IconButton/IconButton';
import {Icon} from '../Icon/Icon';
import {Text} from '../Text/Text';

export interface BottomSheetProps {
  visible: boolean;
  onClose: () => void;
  /** Serif title with ✕; without a title the sheet has only the handle. */
  title?: string;
  testID: string;
  /** Fixed footer below the scrollable content (e.g. primary action). */
  footer?: ReactNode;
}

/** Space the fixed footer takes at the end of the scrollable content. */
const FOOTER_SPACE = 96;
/** Fallback: unmount even if the dismiss callback does not arrive (tests, interrupted animation). */
const UNMOUNT_FALLBACK_MS = 600;

/**
 * Bottom sheet (radius 28, handle, serif title, ✕) on @gorhom/bottom-sheet. It sizes to its
 * content (max 88 % of the screen), scrolls inside, and closes by swiping down (at the top of
 * the content), tapping the backdrop, ✕ or Android back.
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
  const c = theme.colors;
  const insets = useSafeAreaInsets();
  const {height} = useWindowDimensions();
  const ref = useRef<BottomSheetModal>(null);
  const [mounted, setMounted] = useState(visible);
  const visibleRef = useRef(visible);
  visibleRef.current = visible;

  useEffect(() => {
    if (visible) {
      setMounted(true);
      return undefined;
    }
    ref.current?.dismiss();
    const timer = setTimeout(() => setMounted(false), UNMOUNT_FALLBACK_MS);
    return () => clearTimeout(timer);
  }, [visible]);

  useEffect(() => {
    if (mounted && visible) ref.current?.present();
  }, [mounted, visible]);

  // Swipe down, backdrop and Android back end here; report them as a close request.
  const onDismiss = useCallback(() => {
    setMounted(false);
    if (visibleRef.current) onClose();
  }, [onClose]);

  const renderBackdrop = useCallback(
    (props: BottomSheetBackdropProps) => (
      <BottomSheetBackdrop
        {...props}
        appearsOnIndex={0}
        disappearsOnIndex={-1}
        pressBehavior="close"
        opacity={1}
        style={[props.style, {backgroundColor: c.scrim}]}
      />
    ),
    [c.scrim],
  );

  const renderFooter = useCallback(
    (props: BottomSheetFooterProps) =>
      footer ? (
        <BottomSheetFooter {...props}>
          <View
            style={[
              styles.footer,
              {
                backgroundColor: c.sheet,
                borderTopColor: c.outline,
                paddingBottom: Math.max(insets.bottom, 16),
              },
            ]}
          >
            {footer}
          </View>
        </BottomSheetFooter>
      ) : null,
    [footer, c.sheet, c.outline, insets.bottom],
  );

  if (!mounted) return null;

  return (
    <BottomSheetModal
      ref={ref}
      enableDynamicSizing
      maxDynamicContentSize={height * 0.88}
      enablePanDownToClose
      onDismiss={onDismiss}
      backdropComponent={renderBackdrop}
      footerComponent={renderFooter}
      backgroundStyle={{
        backgroundColor: c.sheet,
        borderTopLeftRadius: theme.radius.sheet,
        borderTopRightRadius: theme.radius.sheet,
      }}
      handleIndicatorStyle={{backgroundColor: c.outline, width: 40, height: 5}}
      accessibilityViewIsModal
    >
      <BottomSheetScrollView
        testID={testID}
        keyboardShouldPersistTaps="handled"
        contentContainerStyle={[
          styles.body,
          {
            paddingBottom: footer
              ? FOOTER_SPACE + insets.bottom
              : 22 + insets.bottom,
          },
        ]}
      >
        {title ? (
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
        ) : null}
        {children}
      </BottomSheetScrollView>
    </BottomSheetModal>
  );
}

const styles = StyleSheet.create({
  header: {
    flexDirection: 'row',
    alignItems: 'center',
    justifyContent: 'space-between',
    paddingTop: 4,
  },
  body: {paddingHorizontal: 20, gap: 22},
  footer: {
    flexDirection: 'row',
    alignItems: 'center',
    gap: 16,
    paddingHorizontal: 20,
    paddingTop: 12,
    borderTopWidth: 1,
  },
});
