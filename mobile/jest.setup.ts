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
  maybeCompleteAuthSession: jest.fn(),
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
      canDismiss: jest.fn(() => false),
      dismissAll: jest.fn(),
      dismissTo: jest.fn(),
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

// Secure storage: in-memory map shared with tests via `global`.
const mockSecureStore = new Map<string, string>();
(globalThis as {mockSecureStore?: Map<string, string>}).mockSecureStore =
  mockSecureStore;
jest.mock('expo-secure-store', () => ({
  AFTER_FIRST_UNLOCK_THIS_DEVICE_ONLY: 0,
  getItemAsync: jest.fn(
    async (key: string) => mockSecureStore.get(key) ?? null,
  ),
  setItemAsync: jest.fn(async (key: string, value: string) => {
    mockSecureStore.set(key, value);
  }),
  deleteItemAsync: jest.fn(async (key: string) => {
    mockSecureStore.delete(key);
  }),
}));

// The IdP is never contacted in unit tests; features inject a fake AuthGateway.
jest.mock('expo-auth-session', () => {
  class TokenError extends Error {
    code: string;
    constructor(params: {error: string}) {
      super(params.error);
      this.code = params.error;
    }
  }
  return {
    makeRedirectUri: jest.fn(() => 'stadtfest://auth'),
    fetchDiscoveryAsync: jest.fn(async () => ({
      tokenEndpoint: 'http://idp.test/token',
      revocationEndpoint: 'http://idp.test/revoke',
      authorizationEndpoint: 'http://idp.test/auth',
    })),
    AuthRequest: jest.fn(),
    exchangeCodeAsync: jest.fn(),
    refreshAsync: jest.fn(),
    revokeAsync: jest.fn(async () => true),
    TokenError,
    TokenTypeHint: {RefreshToken: 'refresh_token'},
  };
});

// expo-image-picker / expo-image-manipulator (R08): native modules; tests set the results.
jest.mock('expo-image-picker', () => ({
  requestMediaLibraryPermissionsAsync: jest.fn(async () => ({granted: true})),
  launchImageLibraryAsync: jest.fn(async () => ({
    canceled: true,
    assets: null,
  })),
}));
jest.mock('expo-image-manipulator', () => {
  const context = {
    resize: jest.fn(),
    renderAsync: jest.fn(async () => ({
      saveAsync: jest.fn(async () => ({
        uri: 'file:///prepared.jpg',
        width: 2560,
        height: 1707,
      })),
    })),
  };
  return {
    ImageManipulator: {manipulate: jest.fn(() => context)},
    SaveFormat: {JPEG: 'jpeg', PNG: 'png', WEBP: 'webp'},
    __context: context,
  };
});
