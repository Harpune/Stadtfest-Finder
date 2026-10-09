import React from 'react';
import {StyleSheet, View} from 'react-native';

import {strings} from '@/strings/de';
import {useTheme} from '@/theme';

import {Text} from '../Text/Text';

export interface InvitationCountsProps {
  /** Accepted invitees plus the host. */
  coming: number;
  open: number;
  declined: number;
  testID?: string;
}

/** Three tiles of the invitation overview (06-01): "kommen" amber, "offen", "abgesagt" pink. */
export function InvitationCounts({
  coming,
  open,
  declined,
  testID,
}: InvitationCountsProps) {
  const theme = useTheme();
  const c = theme.colors;
  const s = strings.invitations;
  const tiles = [
    {
      key: 'coming',
      n: coming,
      label: s.coming,
      bg: c.primaryContainer,
      fg: c.primaryText,
    },
    {key: 'open', n: open, label: s.open, bg: c.surface, fg: c.onSurface},
    {
      key: 'declined',
      n: declined,
      label: s.declined,
      bg: c.secondaryContainer,
      fg: c.secondaryText,
    },
  ];
  return (
    <View style={styles.row} testID={testID}>
      {tiles.map(tile => (
        <View
          key={tile.key}
          style={[
            styles.tile,
            {backgroundColor: tile.bg, borderRadius: theme.radius.block},
          ]}
          testID={testID ? `${testID}.${tile.key}` : undefined}
          accessible
          accessibilityLabel={`${tile.n} ${tile.label}`}
        >
          <Text variant="displayL" style={{color: tile.fg}}>
            {tile.n}
          </Text>
          <Text variant="body">{tile.label}</Text>
        </View>
      ))}
    </View>
  );
}

const styles = StyleSheet.create({
  row: {flexDirection: 'row', gap: 10},
  tile: {flex: 1, paddingHorizontal: 14, paddingVertical: 14, gap: 2},
});
