import React from 'react';
import {StyleSheet, View} from 'react-native';

import {strings} from '@/strings/de';
import {useTheme} from '@/theme';

import {Avatar} from '../Avatar/Avatar';
import {Text} from '../Text/Text';

export type InviteeStatus = 'accepted' | 'open' | 'declined';

export interface InviteeRowProps {
  name: string;
  initials: string;
  /** Avatar color; without it the neutral user color (own account). */
  color?: string;
  /** Second line, e.g. "hat zugesagt" or "Eingeladen vor 2 Tagen". */
  meta?: string;
  status: InviteeStatus;
  testID: string;
}

/** Person of an invitation (06-01, 06-03): avatar, name, second line and status pill. */
export function InviteeRow({
  name,
  initials,
  color,
  meta,
  status,
  testID,
}: InviteeRowProps) {
  return (
    <View style={styles.row} testID={testID}>
      <Avatar initials={initials} color={color} size={meta ? 48 : 40} />
      <View style={styles.text}>
        <Text variant="bodyStrong" numberOfLines={1}>
          {name}
        </Text>
        {meta ? (
          <Text variant="meta" tone="muted" numberOfLines={1}>
            {meta}
          </Text>
        ) : null}
      </View>
      <StatusBadge status={status} testID={`${testID}.status`} />
    </View>
  );
}

/** Pill "Zugesagt" (amber), "Offen" (neutral), "Abgesagt" (pink). */
export function StatusBadge({
  status,
  testID,
}: {
  status: InviteeStatus;
  testID?: string;
}) {
  const theme = useTheme();
  const c = theme.colors;
  const [background, foreground] =
    status === 'accepted'
      ? [c.primaryContainer, c.primaryText]
      : status === 'declined'
        ? [c.secondaryContainer, c.secondaryText]
        : [c.surfaceVariant, c.onSurfaceMuted];
  return (
    <View
      testID={testID}
      style={[
        styles.pill,
        {backgroundColor: background, borderRadius: theme.radius.chip},
      ]}
    >
      <Text variant="bodyStrong" style={{color: foreground}}>
        {strings.invitations.status[status]}
      </Text>
    </View>
  );
}

const styles = StyleSheet.create({
  row: {flexDirection: 'row', alignItems: 'center', gap: 14},
  text: {flex: 1, gap: 2},
  pill: {paddingHorizontal: 12, paddingVertical: 6},
});
