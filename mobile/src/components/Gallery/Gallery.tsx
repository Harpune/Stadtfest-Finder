import React, {ReactNode, useState} from 'react';
import {Image, Pressable, StyleSheet, View} from 'react-native';

import {strings} from '@/strings/de';
import {useTheme} from '@/theme';

import {ImagePlaceholder} from '../ImagePlaceholder/ImagePlaceholder';
import {Text} from '../Text/Text';

export const GALLERY_HEIGHT = 340;

export interface GalleryImage {
  url: string;
}

export interface GalleryProps {
  images: readonly GalleryImage[];
  /** Event name for the placeholder caption and accessibility. */
  name: string;
  /** Floating buttons (back, share, heart) rendered on top. */
  overlay?: ReactNode;
  testID?: string;
}

/**
 * Detail gallery (340 high): tapping the left/right half pages, dots (active 18 × 5 amber)
 * and "1 / n" show the position. Without images the striped placeholder is shown.
 */
export function Gallery({images, name, overlay, testID}: GalleryProps) {
  const theme = useTheme();
  const c = theme.colors;
  const [index, setIndex] = useState(0);
  const count = Math.max(images.length, 1);
  const current = images[index];
  const page = (delta: number) => setIndex(i => (i + delta + count) % count);

  return (
    <View testID={testID} style={styles.container}>
      {current ? (
        <Image
          source={{uri: current.url}}
          style={StyleSheet.absoluteFill}
          resizeMode="cover"
        />
      ) : (
        <ImagePlaceholder
          label={strings.detail.galleryCaption(index + 1, name)}
          style={StyleSheet.absoluteFill}
        />
      )}
      {count > 1 ? (
        <View style={StyleSheet.absoluteFill}>
          <View style={styles.halves}>
            <Pressable
              testID={testID ? `${testID}.previous` : undefined}
              accessibilityRole="button"
              accessibilityLabel={strings.detail.galleryPrevious}
              style={styles.half}
              onPress={() => page(-1)}
            />
            <Pressable
              testID={testID ? `${testID}.next` : undefined}
              accessibilityRole="button"
              accessibilityLabel={strings.detail.galleryNext}
              style={styles.half}
              onPress={() => page(1)}
            />
          </View>
        </View>
      ) : null}
      <View style={styles.footer} pointerEvents="none">
        <View style={styles.dots}>
          {Array.from({length: count}, (_, i) => (
            <View
              key={i}
              style={[
                styles.dot,
                i === index
                  ? {width: 18, backgroundColor: c.primary}
                  : {backgroundColor: 'rgba(255,255,255,0.35)'},
              ]}
            />
          ))}
        </View>
        <View style={[styles.counter, {backgroundColor: c.glass}]}>
          <Text
            variant="meta"
            testID={testID ? `${testID}.counter` : undefined}
          >
            {strings.detail.galleryCounter(index + 1, count)}
          </Text>
        </View>
      </View>
      {overlay}
    </View>
  );
}

const styles = StyleSheet.create({
  container: {height: GALLERY_HEIGHT, overflow: 'hidden'},
  halves: {flex: 1, flexDirection: 'row'},
  half: {flex: 1},
  footer: {
    position: 'absolute',
    left: 16,
    right: 16,
    bottom: 44,
    alignItems: 'center',
    justifyContent: 'center',
  },
  dots: {flexDirection: 'row', gap: 6},
  dot: {width: 6, height: 5, borderRadius: 3},
  counter: {
    position: 'absolute',
    right: 0,
    paddingHorizontal: 10,
    paddingVertical: 4,
    borderRadius: 12,
  },
});
