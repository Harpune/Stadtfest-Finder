import React from 'react';
import {StyleSheet, View} from 'react-native';

import {useTheme} from '@/theme';

import {Text} from '../Text/Text';

export interface ClusterMarkerProps {
  count: number;
  testID?: string;
}

/** Cluster: 44 pt rose circle with count and soft rose halo (R03-US2). */
export function ClusterMarker({count, testID}: ClusterMarkerProps) {
  const theme = useTheme();
  const c = theme.colors;
  return (
    <View style={[styles.halo, {backgroundColor: 'rgba(255,107,139,0.25)'}]}>
      <View
        testID={testID}
        style={[
          styles.cluster,
          {backgroundColor: c.secondary, shadowColor: c.secondary},
        ]}
      >
        <Text variant="bodyStrong" style={{color: c.onSecondary, fontSize: 17}}>
          {count > 99 ? '99+' : count}
        </Text>
      </View>
    </View>
  );
}

const styles = StyleSheet.create({
  halo: {
    width: 58,
    height: 58,
    borderRadius: 29,
    alignItems: 'center',
    justifyContent: 'center',
  },
  cluster: {
    width: 44,
    height: 44,
    borderRadius: 22,
    alignItems: 'center',
    justifyContent: 'center',
    shadowOpacity: 0.5,
    shadowRadius: 12,
    shadowOffset: {width: 0, height: 0},
    elevation: 6,
  },
});
