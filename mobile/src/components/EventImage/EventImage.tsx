import {Image} from 'expo-image';
import React, {useState} from 'react';
import {StyleProp, StyleSheet, View, ViewStyle} from 'react-native';

import {ImagePlaceholder} from '../ImagePlaceholder/ImagePlaceholder';

export interface EventImageProps {
  /** Image URL; without it (or if it fails) only the striped placeholder is shown. */
  uri?: string | null;
  /** Placeholder caption, e.g. "Festfoto". */
  label: string;
  style?: StyleProp<ViewStyle>;
  radius?: number;
  /** Accessible description; decorative images leave it out. */
  accessibilityLabel?: string;
  testID?: string;
}

/**
 * Event photo (R08-US4) on expo-image with disk caching. The striped placeholder stays
 * underneath while the image loads and replaces it if loading fails.
 */
export function EventImage({
  uri,
  label,
  style,
  radius = 0,
  accessibilityLabel,
  testID,
}: EventImageProps) {
  const [failed, setFailed] = useState<string | null>(null);
  const show = Boolean(uri) && failed !== uri;
  return (
    <View testID={testID} style={[styles.box, {borderRadius: radius}, style]}>
      <ImagePlaceholder label={label} style={StyleSheet.absoluteFill} />
      {show ? (
        <Image
          source={{uri: uri ?? undefined}}
          style={StyleSheet.absoluteFill}
          contentFit="cover"
          transition={150}
          cachePolicy="disk"
          recyclingKey={uri ?? undefined}
          accessible={Boolean(accessibilityLabel)}
          accessibilityLabel={accessibilityLabel}
          onError={() => setFailed(uri ?? null)}
          testID={testID ? `${testID}.image` : undefined}
        />
      ) : null}
    </View>
  );
}

const styles = StyleSheet.create({
  box: {overflow: 'hidden'},
});
