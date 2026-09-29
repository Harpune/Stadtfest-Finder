/**
 * The map (R03-US2): MapLibre with MapTiler tiles (ADR 0009), React markers with client-side
 * clustering, the selected pin in its own layer and the user's position as a blue dot.
 */
import {
  Camera,
  CameraRef,
  Map,
  Marker,
  UserLocation,
  ViewStateChangeEvent,
} from '@maplibre/maplibre-react-native';
import React, {
  forwardRef,
  useImperativeHandle,
  useMemo,
  useRef,
  useState,
} from 'react';
import {NativeSyntheticEvent, StyleSheet} from 'react-native';

import {ClusterMarker, EventMarker, SelectedPin} from '@/components';
import {strings} from '@/strings/de';
import {useTheme} from '@/theme';

import type {CategoryLook} from './categoryLookup';
import {clusterItems} from './cluster';
import type {Bbox, GeoPoint} from './filter';
import {configureTileRequests, offlineStyle} from './mapStyle';
import {useTileStyle} from './useTileStyle';
import type {EventSummary} from './useDiscoverData';

// Before the first map mounts: the style request must already carry the header.
configureTileRequests();

export const MIN_ZOOM = 6;
export const MAX_ZOOM = 13;
export const LOCATED_ZOOM = 10;

export interface MapViewport {
  center: GeoPoint;
  zoom: number;
  bbox: Bbox;
}

export interface DiscoverMapHandle {
  flyTo: (center: GeoPoint, zoom?: number) => void;
  zoomBy: (delta: number) => void;
  /** Moves the map only if the point is outside the visible area (carousel swipe). */
  ensureVisible: (point: GeoPoint) => void;
}

export interface DiscoverMapProps {
  initialCenter: GeoPoint;
  initialZoom: number;
  items: readonly EventSummary[];
  selectedId: string | null;
  categoryOf: (id: string) => CategoryLook;
  showUserLocation: boolean;
  onViewportChange: (viewport: MapViewport) => void;
  onMarkerPress: (event: EventSummary) => void;
}

export const DiscoverMap = forwardRef<DiscoverMapHandle, DiscoverMapProps>(
  (
    {
      initialCenter,
      initialZoom,
      items,
      selectedId,
      categoryOf,
      showUserLocation,
      onViewportChange,
      onMarkerPress,
    },
    ref,
  ) => {
    const theme = useTheme();
    const camera = useRef<CameraRef>(null);

    // If the tile style cannot be loaded (key revoked, offline), fall back to the offline

    // style so markers and the viewport still work instead of hanging in "loading".

    const [styleFailed, setStyleFailed] = useState(false);

    const tileStyle = useTileStyle(theme.scheme);

    const [viewport, setViewport] = useState<MapViewport>({
      center: initialCenter,
      zoom: initialZoom,
      bbox: [
        initialCenter.lon,
        initialCenter.lat,
        initialCenter.lon,
        initialCenter.lat,
      ],
    });

    useImperativeHandle(
      ref,
      () => ({
        flyTo: (center, zoom = LOCATED_ZOOM) =>
          camera.current?.flyTo({
            center: [center.lon, center.lat],
            zoom,
            duration: 600,
          }),
        zoomBy: delta =>
          camera.current?.zoomTo(
            Math.min(MAX_ZOOM, Math.max(MIN_ZOOM, viewport.zoom + delta)),
            {duration: 250},
          ),
        ensureVisible: point => {
          const [w, s, e, n] = viewport.bbox;
          if (
            point.lon < w ||
            point.lon > e ||
            point.lat < s ||
            point.lat > n
          ) {
            camera.current?.easeTo({
              center: [point.lon, point.lat],
              duration: 400,
            });
          }
        },
      }),
      [viewport],
    );

    const onRegionDidChange = (
      event: NativeSyntheticEvent<ViewStateChangeEvent>,
    ) => {
      const {center, zoom, bounds} = event.nativeEvent;
      const next = {
        center: {lon: center[0], lat: center[1]},
        zoom,
        bbox: bounds as Bbox,
      };
      setViewport(next);
      onViewportChange(next);
    };

    // Recluster only per half zoom level to keep markers stable while pinching.
    const clusterZoom = Math.floor(viewport.zoom * 2) / 2;
    const mapItems = useMemo(
      () =>
        clusterItems(
          items.map(item => ({...item, lat: item.lat, lon: item.lon})),
          clusterZoom,
          selectedId,
        ),
      [items, clusterZoom, selectedId],
    );

    return (
      <Map
        testID="discover.map"
        style={StyleSheet.absoluteFill}
        mapStyle={
          !styleFailed && tileStyle
            ? tileStyle
            : offlineStyle(theme.colors.background)
        }
        onDidFailLoadingMap={() => setStyleFailed(true)}
        logo={false}
        compass={false}
        touchPitch={false}
        touchRotate={false}
        // Visible text attribution is rendered by the screen (MapTiler/OSM require text).
        attribution={false}
        onRegionDidChange={onRegionDidChange}
      >
        <Camera
          ref={camera}
          minZoom={MIN_ZOOM}
          maxZoom={MAX_ZOOM}
          initialViewState={{
            center: [initialCenter.lon, initialCenter.lat],
            zoom: initialZoom,
          }}
        />
        {showUserLocation ? <UserLocation animated accuracy={false} /> : null}
        {mapItems.map(entry => {
          if (entry.kind === 'cluster') {
            return (
              <Marker
                key={entry.key}
                id={entry.key}
                lngLat={[entry.lon, entry.lat]}
                accessibilityLabel={strings.discover.cluster(
                  entry.items.length,
                )}
                onPress={() =>
                  camera.current?.easeTo({
                    center: [entry.lon, entry.lat],
                    zoom: Math.min(MAX_ZOOM, viewport.zoom + 2),
                    duration: 400,
                  })
                }
              >
                <ClusterMarker
                  count={entry.items.length}
                  testID={`discover.cluster.${entry.key}`}
                />
              </Marker>
            );
          }
          const event = entry.item;
          const category = categoryOf(event.categoryId);
          if (event.id === selectedId) {
            // Pill extends towards the screen center.
            const align = event.lon > viewport.center.lon ? 'right' : 'left';
            return (
              <Marker
                key={`selected:${event.id}`}
                id={`selected:${event.id}`}
                lngLat={[event.lon, event.lat]}
                anchor={align}
                offset={[align === 'right' ? 22 : -22, 0]}
                onPress={() => onMarkerPress(event)}
              >
                <SelectedPin
                  label={event.shortName}
                  emoji={category.emoji}
                  align={align}
                  testID={`discover.pin.selected.${event.id}`}
                />
              </Marker>
            );
          }
          return (
            <Marker
              key={event.id}
              id={event.id}
              lngLat={[event.lon, event.lat]}
              accessibilityLabel={event.name}
              onPress={() => onMarkerPress(event)}
            >
              <EventMarker
                emoji={category.emoji}
                color={category.color}
                testID={`discover.pin.${event.id}`}
              />
            </Marker>
          );
        })}
      </Map>
    );
  },
);
DiscoverMap.displayName = 'DiscoverMap';
