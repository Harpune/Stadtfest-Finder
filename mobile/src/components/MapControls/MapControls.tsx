import React from 'react';
import {Pressable, StyleSheet, View} from 'react-native';

import {strings} from '@/strings/de';
import {useTheme} from '@/theme';

import {Icon} from '../Icon/Icon';

export interface MapControlsProps {
  onZoomIn: () => void;
  onZoomOut: () => void;
  /** Hidden when location access is denied. */
  onLocate?: () => void;
  zoomInDisabled?: boolean;
  zoomOutDisabled?: boolean;
}

/** Zoom +/− (48 × 44 each) and the locate button (48 × 48, radius 16). */
export function MapControls({
  onZoomIn,
  onZoomOut,
  onLocate,
  zoomInDisabled = false,
  zoomOutDisabled = false,
}: MapControlsProps) {
  const theme = useTheme();
  const c = theme.colors;
  const box = [
    theme.shadow.floating,
    {
      backgroundColor: c.floating,
      borderColor: c.outline,
      borderRadius: theme.radius.button,
    },
  ];
  return (
    <View style={styles.container}>
      <View style={[styles.zoom, box]}>
        <ControlButton
          icon="plus"
          label={strings.discover.zoomInButton}
          onPress={onZoomIn}
          disabled={zoomInDisabled}
          testID="map.zoomIn"
        />
        <View style={[styles.divider, {backgroundColor: c.outline}]} />
        <ControlButton
          icon="minus"
          label={strings.discover.zoomOutButton}
          onPress={onZoomOut}
          disabled={zoomOutDisabled}
          testID="map.zoomOut"
        />
      </View>
      {onLocate ? (
        <View style={[styles.locate, box]}>
          <ControlButton
            icon="locate"
            label={strings.discover.locate}
            onPress={onLocate}
            color={c.primary}
            testID="map.locate"
            height={48}
          />
        </View>
      ) : null}
    </View>
  );
}

interface ControlButtonProps {
  icon: 'plus' | 'minus' | 'locate';
  label: string;
  onPress: () => void;
  testID: string;
  disabled?: boolean;
  color?: string;
  height?: number;
}

function ControlButton({
  icon,
  label,
  onPress,
  testID,
  disabled = false,
  color,
  height = 44,
}: ControlButtonProps) {
  return (
    <Pressable
      testID={testID}
      accessibilityRole="button"
      accessibilityLabel={label}
      accessibilityState={{disabled}}
      disabled={disabled}
      onPress={onPress}
      style={({pressed}) => [
        styles.button,
        {height, opacity: disabled ? 0.4 : pressed ? 0.7 : 1},
      ]}
    >
      <Icon name={icon} size={22} color={color} />
    </Pressable>
  );
}

const styles = StyleSheet.create({
  container: {gap: 10, alignItems: 'flex-end'},
  zoom: {width: 48, borderWidth: 1, overflow: 'hidden'},
  locate: {width: 48, borderWidth: 1},
  divider: {height: 1},
  button: {width: 48, alignItems: 'center', justifyContent: 'center'},
});
