import React, {useEffect, useRef} from 'react';
import {Animated, Easing, View} from 'react-native';

import {useTheme} from '@/theme';

export interface SpinnerProps {
  /** Ring color; defaults to the primary text color. */
  color?: string;
  size?: number;
  testID?: string;
}

/** 16 pt ring spinner, 2 pt stroke, one turn per 0.8 s (design reference). */
export function Spinner({color, size = 16, testID}: SpinnerProps) {
  const theme = useTheme();
  const rotation = useRef(new Animated.Value(0)).current;

  useEffect(() => {
    const loop = Animated.loop(
      Animated.timing(rotation, {
        toValue: 1,
        duration: 800,
        easing: Easing.linear,
        useNativeDriver: true,
      }),
    );
    loop.start();
    return () => loop.stop();
  }, [rotation]);

  const ringColor = color ?? theme.colors.primaryText;
  const rotate = rotation.interpolate({
    inputRange: [0, 1],
    outputRange: ['0deg', '360deg'],
  });

  return (
    <View
      accessible
      accessibilityRole="progressbar"
      accessibilityLabel="Lädt"
      testID={testID}
    >
      <Animated.View
        style={{
          width: size,
          height: size,
          borderRadius: size / 2,
          borderWidth: 2,
          borderColor: ringColor,
          borderTopColor: 'transparent',
          transform: [{rotate}],
        }}
      />
    </View>
  );
}
