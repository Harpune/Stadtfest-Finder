import {
  Camera,
  type CameraRef,
  Map,
  Marker,
  type StyleSpecification,
} from '@maplibre/maplibre-react-native';
import React, {useEffect, useRef} from 'react';
import {Pressable, StyleSheet, View} from 'react-native';

import {useTheme} from '@/theme';

import {Icon} from '../Icon/Icon';
import {Text} from '../Text/Text';

export interface PinMapProps {
  lat: number | null;
  lon: number | null;
  /** Map view when no pin is set yet, e.g. the own location or all of Germany. */
  fallback: {lat: number; lon: number; zoom: number};
  mapStyle: string | StyleSpecification;
  /** Pin mode (08-07): the frame turns turquoise. */
  active: boolean;
  /** Opens the full-screen picker (`LocationPicker`); without it the map is read-only. */
  onPress?: () => void;
  /** Accessible name of the tap target, e.g. "Tippe, um den Pin zu verschieben". */
  pressLabel?: string;
  /** Label in the lower left corner, e.g. coordinates or "Tippe, um den Pin zu setzen". */
  caption?: string;
  invalid?: boolean;
  testID: string;
}

/**
 * Location preview of the moderation form (08-03, 08-07) with a turquoise pin. The map
 * itself takes no gestures, so it never fights the form's scrolling; a tap opens the
 * full-screen picker instead.
 */
export function PinMap({
  lat,
  lon,
  fallback,
  mapStyle,
  active,
  onPress,
  pressLabel,
  caption,
  invalid = false,
  testID,
}: PinMapProps) {
  const theme = useTheme();
  const c = theme.colors;
  const camera = useRef<CameraRef>(null);
  const hasPin = lat !== null && lon !== null;

  // Follow a new pin from the address search or the picker; without a pin follow the
  // fallback view, which may arrive later (the own location is read asynchronously).
  useEffect(() => {
    if (hasPin) {
      camera.current?.easeTo({center: [lon, lat], zoom: 15, duration: 400});
    } else {
      camera.current?.easeTo({
        center: [fallback.lon, fallback.lat],
        zoom: fallback.zoom,
        duration: 400,
      });
    }
  }, [hasPin, lat, lon, fallback.lat, fallback.lon, fallback.zoom]);

  return (
    <View
      testID={testID}
      style={[
        styles.frame,
        {
          borderRadius: theme.radius.block,
          backgroundColor: c.surface,
          borderColor: invalid ? c.error : active ? c.mod.primary : c.outline,
        },
      ]}
    >
      <Map
        style={StyleSheet.absoluteFill}
        mapStyle={mapStyle}
        logo={false}
        compass={false}
        attribution={false}
        dragPan={false}
        touchZoom={false}
        touchRotate={false}
        touchPitch={false}
        testID={`${testID}.map`}
      >
        <Camera
          ref={camera}
          initialViewState={{
            center: hasPin ? [lon, lat] : [fallback.lon, fallback.lat],
            zoom: hasPin ? 15 : fallback.zoom,
          }}
        />
        {hasPin ? (
          <Marker id="pin" lngLat={[lon, lat]} anchor="bottom">
            <Icon
              name="pin"
              size={40}
              color={c.mod.primary}
              strokeWidth={2.2}
            />
          </Marker>
        ) : null}
      </Map>
      {onPress ? (
        <Pressable
          style={StyleSheet.absoluteFill}
          accessibilityRole="button"
          accessibilityLabel={pressLabel ?? caption}
          onPress={onPress}
          testID={`${testID}.open`}
        />
      ) : null}
      {caption ? (
        <View
          style={[styles.caption, {backgroundColor: c.glass}]}
          pointerEvents="none"
        >
          <Text variant="meta" testID={`${testID}.caption`}>
            {caption}
          </Text>
        </View>
      ) : null}
    </View>
  );
}

const styles = StyleSheet.create({
  frame: {height: 200, overflow: 'hidden', borderWidth: 1.5},
  caption: {
    position: 'absolute',
    left: 10,
    bottom: 10,
    borderRadius: 10,
    paddingHorizontal: 10,
    paddingVertical: 5,
  },
});
