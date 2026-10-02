import React from 'react';
import {Pressable, StyleSheet, View} from 'react-native';

import {strings} from '@/strings/de';
import {useTheme} from '@/theme';

import {EventImage} from '../EventImage/EventImage';
import {Icon} from '../Icon/Icon';
import {Spinner} from '../Spinner/Spinner';
import {Text} from '../Text/Text';

export type ImageTileState = 'ready' | 'uploading' | 'processing' | 'failed';

export interface ImageTile {
  /** Image ID, or a local key while uploading. */
  key: string;
  state: ImageTileState;
  /** Thumbnail URL (ready) or local file (uploading). */
  uri?: string | null;
}

export interface ImageGridProps {
  tiles: readonly ImageTile[];
  /** Shows the "+ Hochladen" tile. */
  canAdd: boolean;
  onAdd: () => void;
  onRemove: (key: string) => void;
  onRetry: (key: string) => void;
  /** Long press on a ready image, e.g. a menu with "Als Titelbild". */
  onLongPress?: (key: string) => void;
  disabled?: boolean;
  testID: string;
}

const COLUMNS = 3;
const GAP = 10;

/**
 * Image grid of the moderation form (08-04): three columns, the first image is labeled
 * "Titelbild", ✕ removes, a dashed tile uploads. Uploading and processing tiles show a
 * spinner, failed ones "Erneut versuchen".
 */
export function ImageGrid({
  tiles,
  canAdd,
  onAdd,
  onRemove,
  onRetry,
  onLongPress,
  disabled = false,
  testID,
}: ImageGridProps) {
  const theme = useTheme();
  const c = theme.colors;
  const radius = theme.radius.block;
  const tileStyle = [styles.tile, {borderRadius: radius}];
  return (
    <View style={styles.grid} testID={testID}>
      {tiles.map((tile, index) => (
        <View key={tile.key} style={styles.cell}>
          <Pressable
            accessibilityRole="imagebutton"
            accessibilityLabel={
              index === 0
                ? strings.mod.images.coverTile
                : strings.mod.images.tile(index + 1)
            }
            accessibilityHint={
              tile.state === 'ready' && onLongPress
                ? strings.mod.images.longPressHint
                : undefined
            }
            disabled={disabled || tile.state !== 'ready' || !onLongPress}
            onLongPress={() => onLongPress?.(tile.key)}
            style={tileStyle}
            testID={`${testID}.tile.${index}`}
          >
            <EventImage
              uri={
                tile.state === 'ready' || tile.state === 'uploading'
                  ? tile.uri
                  : null
              }
              label=""
              style={StyleSheet.absoluteFill}
              radius={radius}
            />
            {tile.state === 'uploading' || tile.state === 'processing' ? (
              <View style={[styles.overlay, {backgroundColor: c.scrim}]}>
                <Spinner color={c.onSurface} />
                <Text variant="meta" style={styles.overlayText}>
                  {tile.state === 'uploading'
                    ? strings.mod.images.uploading
                    : strings.mod.images.processing}
                </Text>
              </View>
            ) : null}
            {tile.state === 'failed' ? (
              <Pressable
                accessibilityRole="button"
                onPress={() => onRetry(tile.key)}
                disabled={disabled}
                style={[styles.overlay, {backgroundColor: c.scrim}]}
                testID={`${testID}.tile.${index}.retry`}
              >
                <Text variant="meta" tone="error" style={styles.overlayText}>
                  {strings.mod.images.failed}
                </Text>
                <Text
                  variant="bodyStrong"
                  tone="mod"
                  style={styles.overlayText}
                >
                  {strings.mod.images.retry}
                </Text>
              </Pressable>
            ) : null}
            {index === 0 && tile.state === 'ready' ? (
              <View
                style={[
                  styles.cover,
                  {backgroundColor: c.mod.primary, borderRadius: 8},
                ]}
              >
                <Text
                  variant="meta"
                  style={{
                    color: c.mod.onPrimary,
                    fontFamily: theme.fonts.semibold,
                  }}
                >
                  {strings.mod.images.cover}
                </Text>
              </View>
            ) : null}
          </Pressable>
          {tile.state !== 'uploading' && !disabled ? (
            <Pressable
              accessibilityRole="button"
              accessibilityLabel={strings.mod.images.remove(index + 1)}
              hitSlop={8}
              onPress={() => onRemove(tile.key)}
              style={[styles.remove, {backgroundColor: c.scrim}]}
              testID={`${testID}.tile.${index}.remove`}
            >
              <Icon name="close" size={16} color="#FFFFFF" />
            </Pressable>
          ) : null}
        </View>
      ))}
      {canAdd && !disabled ? (
        <View style={styles.cell}>
          <Pressable
            accessibilityRole="button"
            accessibilityLabel={strings.mod.images.add}
            onPress={onAdd}
            style={({pressed}) => [
              tileStyle,
              styles.add,
              {borderColor: c.outline, opacity: pressed ? 0.7 : 1},
            ]}
            testID={`${testID}.add`}
          >
            <Text variant="bodyStrong" tone="mod">
              {strings.mod.images.add}
            </Text>
          </Pressable>
        </View>
      ) : null}
    </View>
  );
}

const styles = StyleSheet.create({
  grid: {flexDirection: 'row', flexWrap: 'wrap', marginHorizontal: -GAP / 2},
  cell: {width: `${100 / COLUMNS}%`, padding: GAP / 2},
  tile: {aspectRatio: 1, overflow: 'hidden'},
  overlay: {
    ...StyleSheet.absoluteFill,
    alignItems: 'center',
    justifyContent: 'center',
    gap: 6,
    padding: 8,
  },
  overlayText: {textAlign: 'center'},
  cover: {
    position: 'absolute',
    left: 8,
    bottom: 8,
    paddingHorizontal: 8,
    paddingVertical: 3,
  },
  remove: {
    position: 'absolute',
    top: GAP / 2 + 8,
    right: GAP / 2 + 8,
    width: 32,
    height: 32,
    borderRadius: 16,
    alignItems: 'center',
    justifyContent: 'center',
  },
  add: {
    borderWidth: 1.5,
    borderStyle: 'dashed',
    alignItems: 'center',
    justifyContent: 'center',
  },
});
