import React from 'react';
import {StyleSheet, View} from 'react-native';

import {strings} from '@/strings/de';
import {useTheme} from '@/theme';

import {Button} from '../Button/Button';
import {Icon} from '../Icon/Icon';
import {IconButton} from '../IconButton/IconButton';
import {Spinner} from '../Spinner/Spinner';
import {Text} from '../Text/Text';

export type AiSearchBannerState = 'running' | 'found' | 'nothing' | 'failed';

export interface AiSearchBannerProps {
  state: AiSearchBannerState;
  text: string;
  /** "Prüfen" when finds are waiting. */
  onReview?: () => void;
  /** "Erneut versuchen" after a failure. */
  onRetry?: () => void;
  /** ✕ (not while running). */
  onDismiss?: () => void;
  testID: string;
}

/**
 * Status bar of the AI search in the moderation overview (09-02, 09-03): spinner while it
 * runs, then the result with "Prüfen", or the failure with "Erneut versuchen".
 */
export function AiSearchBanner({
  state,
  text,
  onReview,
  onRetry,
  onDismiss,
  testID,
}: AiSearchBannerProps) {
  const theme = useTheme();
  const c = theme.colors;
  return (
    <View
      testID={testID}
      accessibilityRole={state === 'running' ? 'progressbar' : 'summary'}
      accessibilityLiveRegion="polite"
      style={[
        styles.bar,
        {
          backgroundColor: state === 'failed' ? c.errorContainer : c.mod.banner,
          borderRadius: theme.radius.block,
        },
      ]}
    >
      {state === 'running' ? <Spinner color={c.mod.text} /> : null}
      <Text
        variant="bodyStrong"
        tone={state === 'failed' ? 'error' : 'default'}
        style={styles.text}
        testID={`${testID}.text`}
      >
        {text}
      </Text>
      {state === 'found' && onReview ? (
        <Button
          label={strings.mod.ai.review}
          variant="mod"
          size="medium"
          onPress={onReview}
          testID={`${testID}.review`}
        />
      ) : null}
      {state === 'failed' && onRetry ? (
        <Button
          label={strings.mod.ai.retry}
          variant="secondary"
          size="medium"
          onPress={onRetry}
          testID={`${testID}.retry`}
        />
      ) : null}
      {state !== 'running' && onDismiss ? (
        <IconButton
          icon={<Icon name="close" size={20} />}
          accessibilityLabel={strings.mod.ai.dismiss}
          onPress={onDismiss}
          variant="glass"
          size={40}
          testID={`${testID}.dismiss`}
        />
      ) : null}
    </View>
  );
}

const styles = StyleSheet.create({
  bar: {
    flexDirection: 'row',
    alignItems: 'center',
    gap: 12,
    paddingVertical: 12,
    paddingLeft: 16,
    paddingRight: 8,
    minHeight: 64,
  },
  text: {flex: 1},
});
