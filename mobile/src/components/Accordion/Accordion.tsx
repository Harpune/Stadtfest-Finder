import React, {PropsWithChildren} from 'react';
import {Pressable, StyleSheet, View} from 'react-native';

import {useTheme} from '@/theme';

import {Icon} from '../Icon/Icon';
import {Text} from '../Text/Text';

export interface AccordionProps {
  title: string;
  /** Short state shown under the title, e.g. "2 Filter aktiv". */
  summary?: string;
  expanded: boolean;
  onToggle: () => void;
  disabled?: boolean;
  /** `mod`: turquoise chevron (moderation view). */
  accent?: 'primary' | 'mod';
  testID: string;
}

/**
 * Collapsible section: a header row with title, optional summary and chevron; the content
 * is only rendered while expanded. The caller owns the state, so a form can keep it.
 */
export function Accordion({
  title,
  summary,
  expanded,
  onToggle,
  disabled = false,
  accent = 'primary',
  testID,
  children,
}: PropsWithChildren<AccordionProps>) {
  const theme = useTheme();
  const c = theme.colors;
  return (
    <View
      style={[
        styles.box,
        {backgroundColor: c.surfaceVariant, borderRadius: theme.radius.block},
      ]}
    >
      <Pressable
        testID={testID}
        accessibilityRole="button"
        accessibilityLabel={title}
        accessibilityState={{expanded, disabled}}
        disabled={disabled}
        onPress={onToggle}
        style={({pressed}) => [
          styles.header,
          {opacity: disabled ? 0.5 : pressed ? 0.8 : 1},
        ]}
      >
        <View style={styles.text}>
          <Text variant="bodyStrong">{title}</Text>
          {summary ? (
            <Text variant="caption" tone="muted" testID={`${testID}.summary`}>
              {summary}
            </Text>
          ) : null}
        </View>
        <View style={expanded ? styles.open : undefined}>
          <Icon
            name="chevronDown"
            size={20}
            color={accent === 'mod' ? c.mod.primary : c.onSurfaceMuted}
          />
        </View>
      </Pressable>
      {expanded ? (
        <View style={styles.content} testID={`${testID}.content`}>
          {children}
        </View>
      ) : null}
    </View>
  );
}

const styles = StyleSheet.create({
  box: {overflow: 'hidden'},
  header: {
    flexDirection: 'row',
    alignItems: 'center',
    gap: 12,
    paddingHorizontal: 16,
    paddingVertical: 14,
  },
  text: {flex: 1, gap: 2},
  open: {transform: [{rotate: '180deg'}]},
  content: {gap: 16, paddingHorizontal: 16, paddingBottom: 16},
});
