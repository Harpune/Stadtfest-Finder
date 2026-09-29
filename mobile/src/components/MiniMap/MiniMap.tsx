import {
  Camera,
  Map,
  Marker,
  type StyleSpecification,
} from '@maplibre/maplibre-react-native';
import React from 'react';
import {Pressable, StyleSheet, View} from 'react-native';

import {strings} from '@/strings/de';
import {useTheme} from '@/theme';

import {Text} from '../Text/Text';

export interface MiniMapProps {
  lat: number;
  lon: number;
  emoji: string;
  mapStyle: string | StyleSpecification;
  onPress: () => void;
  testID?: string;
}

function styleKey(style: string | StyleSpecification): string {
  return typeof style === 'string'
    ? style
    : `${style.name ?? 'style'}:${style.layers.length}`;
}

/** Static mini map (160 high) with a centered amber pin; a tap starts the route. */
export function MiniMap({
  lat,
  lon,
  emoji,
  mapStyle,
  onPress,
  testID,
}: MiniMapProps) {
  const theme = useTheme();
  const c = theme.colors;
  return (
    <Pressable
      testID={testID}
      accessibilityRole="button"
      accessibilityLabel={strings.detail.openRoute}
      onPress={onPress}
      style={[
        styles.frame,
        {borderRadius: theme.radius.block, backgroundColor: c.surface},
      ]}
    >
      <View style={StyleSheet.absoluteFill} pointerEvents="none">
        <Map
          // Remount when the style changes (offline -> MapTiler): a second map instance
          // otherwise keeps the style background but never draws the vector tiles.
          key={styleKey(mapStyle)}
          style={StyleSheet.absoluteFill}
          mapStyle={mapStyle}
          dragPan={false}
          touchZoom={false}
          doubleTapZoom={false}
          doubleTapHoldZoom={false}
          touchRotate={false}
          touchPitch={false}
          logo={false}
          compass={false}
          attribution={false}
        >
          <Camera initialViewState={{center: [lon, lat], zoom: 14}} />
          <Marker id="event" lngLat={[lon, lat]}>
            <View
              style={[
                styles.pin,
                {backgroundColor: c.primary, shadowColor: c.primary},
              ]}
            >
              <Text style={styles.emoji}>{emoji}</Text>
            </View>
          </Marker>
        </Map>
      </View>
    </Pressable>
  );
}

const styles = StyleSheet.create({
  frame: {height: 160, overflow: 'hidden'},
  pin: {
    width: 40,
    height: 40,
    borderRadius: 20,
    alignItems: 'center',
    justifyContent: 'center',
    shadowOpacity: 0.55,
    shadowRadius: 14,
    shadowOffset: {width: 0, height: 0},
    elevation: 8,
  },
  emoji: {fontSize: 18, lineHeight: 22},
});
