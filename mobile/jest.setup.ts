// Global test setup: native modules that need mocks in Jest.
import 'react-native-gesture-handler/jestSetup';

jest.mock('@react-native-async-storage/async-storage', () =>
  require('@react-native-async-storage/async-storage/jest/async-storage-mock'),
);

// Spies for MapLibre camera calls (map movements), shared with tests via `global`.
const mockCameraApi = {
  easeTo: jest.fn(),
  flyTo: jest.fn(),
  zoomTo: jest.fn(),
  jumpTo: jest.fn(),
};
(globalThis as {mockCameraApi?: typeof mockCameraApi}).mockCameraApi =
  mockCameraApi;

// MapLibre is native-only: render its components as plain views. The Map reports one
// viewport around Aalen after mounting so screens can start their queries.
jest.mock('@maplibre/maplibre-react-native', () => {
  const React = require('react');
  interface MockMapProps {
    children?: unknown;
    testID?: string;
    onRegionDidChange?: (event: {nativeEvent: object}) => void;
    onPress?: () => void;
  }
  interface MockMarkerProps {
    children?: unknown;
    id?: string;
    onPress?: () => void;
  }
  const Map = ({
    children,
    onRegionDidChange,
    onPress,
    testID,
  }: MockMapProps) => {
    React.useEffect(() => {
      onRegionDidChange?.({
        nativeEvent: {
          center: [10.09, 48.84],
          zoom: 10,
          bearing: 0,
          pitch: 0,
          bounds: [9.6, 48.6, 10.6, 49.1],
          animated: false,
          userInteraction: false,
        },
      });
    }, []);
    return React.createElement(
      require('react-native').Pressable,
      {testID, onPress},
      children,
    );
  };
  // Camera methods are spies on a shared object so tests can assert map movements.
  const Camera = React.forwardRef((_props: unknown, ref: unknown) => {
    React.useImperativeHandle(ref, () => mockCameraApi);
    return null;
  });
  const Marker = ({children, onPress, id}: MockMarkerProps) =>
    React.createElement(
      require('react-native').Pressable,
      {testID: `marker.${id}`, onPress},
      children,
    );
  return {
    Map,
    Camera,
    Marker,
    UserLocation: () => null,
  };
});

jest.mock('expo-location', () => ({
  requestForegroundPermissionsAsync: jest.fn(async () => ({granted: false})),
  getLastKnownPositionAsync: jest.fn(async () => null),
  getCurrentPositionAsync: jest.fn(),
  Accuracy: {Balanced: 3},
}));
