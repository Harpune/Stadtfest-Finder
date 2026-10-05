import {
  Camera,
  type CameraRef,
  Map,
  type StyleSpecification,
} from '@maplibre/maplibre-react-native';
import React, {useRef, useState} from 'react';
import {Modal, StyleSheet, View} from 'react-native';
import {useSafeAreaInsets} from 'react-native-safe-area-context';

import {strings} from '@/strings/de';
import {useTheme} from '@/theme';

import {Button} from '../Button/Button';
import {Icon} from '../Icon/Icon';
import {IconButton} from '../IconButton/IconButton';
import {MapControls} from '../MapControls/MapControls';
import {Text} from '../Text/Text';

const MIN_ZOOM = 5;
const MAX_ZOOM = 19;
/** Zoom for an existing pin: close enough to see streets and squares. */
const PIN_ZOOM = 16;
const START_ZOOM = 12;

export interface LocationPickerProps {
  visible: boolean;
  /** Start position: the current pin, the geocoded address or a default center. */
  start: {lat: number; lon: number};
  /** True if `start` is an exact location (zooms in further). */
  exact: boolean;
  mapStyle: string | StyleSpecification;
  onConfirm: (lat: number, lon: number) => void;
  onCancel: () => void;
  testID: string;
}

/**
 * Full-screen location picker of the moderation form (08-07): the moderator moves and
 * zooms the map, the pin stays fixed in the middle, "Pin übernehmen" takes the center.
 * Android back and ✕ cancel without changes.
 */
export function LocationPicker({
  visible,
  start,
  exact,
  mapStyle,
  onConfirm,
  onCancel,
  testID,
}: LocationPickerProps) {
  const theme = useTheme();
  const c = theme.colors;
  const insets = useSafeAreaInsets();
  const camera = useRef<CameraRef>(null);
  const [center, setCenter] = useState(start);
  const [zoom, setZoom] = useState(exact ? PIN_ZOOM : START_ZOOM);

  const zoomBy = (delta: number) =>
    camera.current?.zoomTo(
      Math.min(MAX_ZOOM, Math.max(MIN_ZOOM, zoom + delta)),
      {duration: 250},
    );

  return (
    <Modal
      visible={visible}
      animationType="slide"
      onRequestClose={onCancel}
      onShow={() => {
        setCenter(start);
        setZoom(exact ? PIN_ZOOM : START_ZOOM);
      }}
      statusBarTranslucent
      navigationBarTranslucent
    >
      <View
        testID={testID}
        style={[styles.root, {backgroundColor: c.background}]}
      >
        <Map
          style={StyleSheet.absoluteFill}
          mapStyle={mapStyle}
          logo={false}
          compass={false}
          attribution={false}
          touchRotate={false}
          touchPitch={false}
          onRegionIsChanging={event => {
            const [lon, lat] = event.nativeEvent.center;
            setCenter({lat, lon});
          }}
          onRegionDidChange={event => {
            const [lon, lat] = event.nativeEvent.center;
            setCenter({lat, lon});
            setZoom(event.nativeEvent.zoom);
          }}
          testID={`${testID}.map`}
        >
          <Camera
            ref={camera}
            initialViewState={{
              center: [start.lon, start.lat],
              zoom: exact ? PIN_ZOOM : START_ZOOM,
            }}
          />
        </Map>

        {/* Fixed pin: its tip marks the map center. */}
        <View style={styles.pinLayer} pointerEvents="none">
          <View style={styles.pin}>
            <Icon
              name="pin"
              size={48}
              color={c.mod.primary}
              strokeWidth={2.2}
            />
          </View>
          <View style={[styles.dot, {backgroundColor: c.mod.primary}]} />
        </View>

        <View
          style={[
            styles.top,
            theme.shadow.floating,
            {
              top: insets.top + 12,
              backgroundColor: c.floating,
              borderColor: c.outline,
              borderRadius: theme.radius.input,
            },
          ]}
        >
          <View style={styles.topText}>
            <Text variant="bodyStrong" accessibilityRole="header">
              {strings.mod.picker.title}
            </Text>
            <Text variant="meta" tone="muted">
              {strings.mod.picker.hint}
            </Text>
          </View>
          <IconButton
            icon={<Icon name="close" size={20} />}
            accessibilityLabel={strings.common.close}
            onPress={onCancel}
            variant="surface"
            size={40}
            testID={`${testID}.close`}
          />
        </View>

        <View style={[styles.controls, {bottom: insets.bottom + 100}]}>
          <MapControls
            onZoomIn={() => zoomBy(1)}
            onZoomOut={() => zoomBy(-1)}
            zoomInDisabled={zoom >= MAX_ZOOM}
            zoomOutDisabled={zoom <= MIN_ZOOM}
          />
        </View>

        <View style={[styles.bottom, {paddingBottom: insets.bottom + 16}]}>
          <Text
            variant="meta"
            style={[styles.coords, {backgroundColor: c.glass}]}
            testID={`${testID}.coords`}
          >
            {`${center.lat.toFixed(5)}, ${center.lon.toFixed(5)}`}
          </Text>
          <Button
            label={strings.mod.picker.confirm}
            variant="mod"
            onPress={() => onConfirm(center.lat, center.lon)}
            testID={`${testID}.confirm`}
          />
        </View>
      </View>
    </Modal>
  );
}

const PIN_SIZE = 48;

const styles = StyleSheet.create({
  root: {flex: 1},
  pinLayer: {
    position: 'absolute',
    top: 0,
    right: 0,
    bottom: 0,
    left: 0,
    alignItems: 'center',
    justifyContent: 'center',
  },
  // Lift the icon by half its height so its tip, not its middle, sits on the center.
  pin: {marginBottom: PIN_SIZE},
  dot: {
    position: 'absolute',
    width: 6,
    height: 6,
    borderRadius: 3,
  },
  top: {
    position: 'absolute',
    left: 16,
    right: 16,
    flexDirection: 'row',
    alignItems: 'center',
    gap: 12,
    paddingVertical: 10,
    paddingLeft: 16,
    paddingRight: 10,
    borderWidth: 1,
  },
  topText: {flex: 1, gap: 2},
  controls: {position: 'absolute', right: 16},
  bottom: {
    position: 'absolute',
    left: 16,
    right: 16,
    bottom: 0,
    gap: 10,
  },
  coords: {
    alignSelf: 'flex-start',
    borderRadius: 10,
    paddingHorizontal: 10,
    paddingVertical: 5,
    overflow: 'hidden',
  },
});
