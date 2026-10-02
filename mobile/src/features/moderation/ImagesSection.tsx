/**
 * "Bilder" in the moderation form (08-04, R08-US1 to US3): pick from the library, upload,
 * show processing, set the cover by long press, remove and retry.
 */
import * as ImagePicker from 'expo-image-picker';
import React, {useEffect, useMemo, useRef, useState} from 'react';
import {StyleSheet, View} from 'react-native';

import {
  BottomSheet,
  Button,
  ImageGrid,
  type ImageTile,
  Text,
  useToast,
} from '@/components';
import {strings} from '@/strings/de';

import {
  imageApi,
  type ImageResult,
  MAX_IMAGES,
  type ModImage,
  preparePhoto,
  uploadPhoto,
} from './images';

/** How often processing images are checked. */
const POLL_MS = 2000;

interface Pending {
  key: string;
  uri: string;
}

export interface ImagesSectionProps {
  eventId: string | null;
  images: readonly ModImage[];
  disabled: boolean;
  /** Returns the event ID, saving a new event as draft first; null if that is impossible. */
  ensureEvent: () => Promise<string | null>;
}

export function ImagesSection({
  eventId,
  images: initial,
  disabled,
  ensureEvent,
}: ImagesSectionProps) {
  const toast = useToast();
  const [images, setImages] = useState<ModImage[]>(() => [...initial]);
  const [pending, setPending] = useState<Pending[]>([]);
  const [menuFor, setMenuFor] = useState<string | null>(null);
  const counter = useRef(0);

  // Poll while the worker is still processing images.
  const processing = images.some(image => image.status === 'processing');
  useEffect(() => {
    if (!eventId || !processing) return undefined;
    const timer = setInterval(() => {
      void imageApi.list(eventId).then(next => {
        if (next) setImages(next);
      });
    }, POLL_MS);
    return () => clearInterval(timer);
  }, [eventId, processing]);

  const tiles = useMemo<ImageTile[]>(
    () => [
      ...images.map(image => ({
        key: image.id,
        state: image.status,
        uri: image.image?.thumbUrl ?? null,
      })),
      ...pending.map(item => ({
        key: item.key,
        state: 'uploading' as const,
        uri: item.uri,
      })),
    ],
    [images, pending],
  );
  const remaining = MAX_IMAGES - images.length - pending.length;

  const add = async () => {
    const permission = await ImagePicker.requestMediaLibraryPermissionsAsync();
    if (!permission.granted) {
      toast(strings.mod.images.permissionDenied);
      return;
    }
    const picked = await ImagePicker.launchImageLibraryAsync({
      mediaTypes: ['images'],
      allowsMultipleSelection: true,
      selectionLimit: remaining,
      quality: 1,
      exif: false,
    });
    if (picked.canceled || picked.assets.length === 0) return;
    const id = await ensureEvent();
    if (!id) return;
    const items = picked.assets.slice(0, remaining).map(asset => ({
      asset,
      key: `upload-${++counter.current}`,
    }));
    setPending(current => [
      ...current,
      ...items.map(({asset, key}) => ({key, uri: asset.uri})),
    ]);
    // One after the other: keeps the order of the selection and the phone responsive.
    for (const {asset, key} of items) {
      const result = await preparePhoto(asset)
        .then(file => uploadPhoto(id, file))
        .catch((): ImageResult<ModImage> => ({ok: false, status: 0}));
      setPending(current => current.filter(item => item.key !== key));
      if (result.ok) {
        const image = result.value;
        setImages(current => [...current, image]);
      } else {
        toast(
          result.error?.error === 'too_many_images'
            ? strings.mod.images.tooMany
            : strings.mod.images.uploadFailed,
        );
      }
    }
  };

  const remove = async (key: string) => {
    if (!eventId) return;
    const before = images;
    setImages(current => current.filter(image => image.id !== key));
    if (!(await imageApi.remove(eventId, key))) {
      setImages(before);
      toast(strings.mod.toast.failed);
    }
  };

  const retry = async (key: string) => {
    if (!eventId) return;
    const result = await imageApi.retry(eventId, key);
    if (result.ok) {
      setImages(current =>
        current.map(image => (image.id === key ? result.value : image)),
      );
    } else {
      toast(strings.mod.images.uploadFailed);
    }
  };

  const makeCover = async (key: string) => {
    setMenuFor(null);
    if (!eventId) return;
    const ids = [key, ...images.map(i => i.id).filter(id => id !== key)];
    const result = await imageApi.order(eventId, ids);
    if (result.ok) {
      setImages(result.value);
      toast(strings.mod.images.coverSet);
    } else {
      toast(strings.mod.toast.failed);
    }
  };

  return (
    <View style={styles.section} testID="mod.form.images">
      <Text variant="label">{strings.mod.images.title}</Text>
      <ImageGrid
        tiles={tiles}
        canAdd={remaining > 0}
        onAdd={() => void add()}
        onRemove={key => void remove(key)}
        onRetry={key => void retry(key)}
        onLongPress={key => setMenuFor(key)}
        disabled={disabled}
        testID="mod.form.images.grid"
      />
      <Text variant="caption" tone="muted">
        {strings.mod.images.rightsHint}
      </Text>
      <BottomSheet
        visible={menuFor !== null}
        onClose={() => setMenuFor(null)}
        testID="mod.form.images.menu"
      >
        <View style={styles.menu}>
          {menuFor !== null && images[0]?.id !== menuFor ? (
            <Button
              label={strings.mod.images.makeCover}
              variant="secondary"
              onPress={() => void makeCover(menuFor)}
              testID="mod.form.images.menu.cover"
            />
          ) : null}
          <Button
            label={strings.mod.images.removeImage}
            variant="danger"
            onPress={() => {
              const key = menuFor;
              setMenuFor(null);
              if (key) void remove(key);
            }}
            testID="mod.form.images.menu.remove"
          />
          <Button
            label={strings.mod.form.menuClose}
            variant="ghost"
            onPress={() => setMenuFor(null)}
            testID="mod.form.images.menu.close"
          />
        </View>
      </BottomSheet>
    </View>
  );
}

const styles = StyleSheet.create({
  section: {gap: 8},
  menu: {gap: 10, paddingBottom: 8},
});
