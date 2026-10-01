import {
  Camera,
  type CameraRef,
  Map,
  Marker,
  type StyleSpecification,
} from '@maplibre/maplibre-react-native';
import React, {useEffect, useRef} from 'react';
import {StyleSheet, View} from 'react-native';

import {useTheme} from '@/theme';

import {Icon} from '../Icon/Icon';
import {Text} from '../Text/Text';

export interface PinMapProps {
  lat: number | null;
  lon: number | null;
  /** Map center when no pin is set yet (e.g. the region). */
  fallback: {lat: number; lon: number};
  mapStyle: string | StyleSpecification;
  /** Pin mode (08-07): a tap sets the pin; the frame turns turquoise. */
  editable: boolean;
  onPick: (lat: number, lon: number) => void;
  /** Label in the lower left corner, e.g. coordinates or "Tippe, um den Pin zu setzen". */
  caption?: string;
  invalid?: boolean;
  testID: string;
}

/** Location map of the moderation form (08-03, 08-07) with a turquoise pin. */
export function PinMap({
  lat,
  lon,
  fallback,
  mapStyle,
  editable,
  onPick,
  caption,
  invalid = false,
  testID,
}: PinMapProps) {
  const theme = useTheme();
  const c = theme.colors;
  const camera = useRef<CameraRef>(null);
  const hasPin = lat !== null && lon !== null;

  // Follow a new pin from the address search; taps in pin mode keep the camera still.
  useEffect(() => {
    if (hasPin && !editable) {
      camera.current?.easeTo({center: [lon, lat], zoom: 14, duration: 400});
    }
  }, [hasPin, lat, lon, editable]);

  return (
    <View
      testID={testID}
      style={[
        styles.frame,
        {
          borderRadius: theme.radius.block,
          backgroundColor: c.surface,
          borderColor: invalid ? c.error : editable ? c.mod.primary : c.outline,
        },
      ]}
    >
      <Map
        style={StyleSheet.absoluteFill}
        mapStyle={mapStyle}
        logo={false}
        compass={false}
        attribution={false}
        touchRotate={false}
        touchPitch={false}
        onPress={event => {
          if (!editable) return;
          const [pressedLon, pressedLat] = event.nativeEvent.lngLat;
          onPick(pressedLat, pressedLon);
        }}
        testID={`${testID}.map`}
      >
        <Camera
          ref={camera}
          initialViewState={{
            center: hasPin ? [lon, lat] : [fallback.lon, fallback.lat],
            zoom: hasPin ? 14 : 9,
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
  frame: {height: 180, overflow: 'hidden', borderWidth: 1.5},
  caption: {
    position: 'absolute',
    left: 10,
    bottom: 10,
    borderRadius: 10,
    paddingHorizontal: 10,
    paddingVertical: 5,
  },
});
