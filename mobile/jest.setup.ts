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
  getForegroundPermissionsAsync: jest.fn(async () => ({
    granted: false,
    canAskAgain: true,
  })),
  getLastKnownPositionAsync: jest.fn(async () => null),
  getCurrentPositionAsync: jest.fn(),
  Accuracy: {Balanced: 3},
}));

jest.mock('expo-web-browser', () => ({
  openBrowserAsync: jest.fn(async () => ({type: 'opened'})),
}));

// Navigation spies; screens are rendered without a navigator in unit tests.
jest.mock('expo-router', () => {
  const actual = jest.requireActual('expo-router');
  return {
    ...actual,
    router: {
      push: jest.fn(),
      back: jest.fn(),
      replace: jest.fn(),
      canGoBack: jest.fn(() => true),
    },
  };
});

// @gorhom/bottom-sheet: official mock, but the modal renders its footer too so sheet actions
// are testable. Gestures (swipe down) are covered by Maestro flows.
jest.mock('@gorhom/bottom-sheet', () => {
  const mock = require('@gorhom/bottom-sheet/mock');
  const React = require('react');
  const {View} = require('react-native');
  class MockBottomSheetModal extends React.Component<{
    children?: unknown;
    footerComponent?: (props: object) => unknown;
  }> {
    present() {}
    dismiss() {}
    close() {}
    render() {
      const {children, footerComponent} = this.props;
      return React.createElement(
        View,
        null,
        children,
        footerComponent?.({}) ?? null,
      );
    }
  }
  return {
    ...mock,
    BottomSheetModal: MockBottomSheetModal,
    BottomSheetFooter: ({children}: {children?: unknown}) => children,
  };
});
