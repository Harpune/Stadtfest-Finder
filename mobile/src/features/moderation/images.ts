/**
 * Event images in the moderation form (R08): prepare a photo on the device, upload it with
 * a signed URL directly into the object storage, then attach it to the event.
 */
import {ImageManipulator, SaveFormat} from 'expo-image-manipulator';

import {fetchClient} from '@/api/client';
import type {components} from '@/api/generated/schema';

export type ModImage = components['schemas']['ModImage'];
type ApiError = components['schemas']['Error'];

/** Longest edge after client-side scaling (R08-US1). */
export const MAX_EDGE = 2560;
const JPEG_QUALITY = 0.85;
export const MAX_IMAGES = 12;

export type ImageResult<T> =
  {ok: true; value: T} | {ok: false; status: number; error?: ApiError};

/** A photo picked from the library. */
export interface PickedPhoto {
  uri: string;
  width: number;
  height: number;
}

/** Scale to at most 2,560 px and save as JPEG (quality 0.85); returns the local file. */
export async function preparePhoto(photo: PickedPhoto): Promise<string> {
  const context = ImageManipulator.manipulate(photo.uri);
  if (Math.max(photo.width, photo.height) > MAX_EDGE) {
    context.resize(
      photo.width >= photo.height
        ? {width: MAX_EDGE, height: null}
        : {width: null, height: MAX_EDGE},
    );
  }
  const rendered = await context.renderAsync();
  const saved = await rendered.saveAsync({
    format: SaveFormat.JPEG,
    compress: JPEG_QUALITY,
  });
  return saved.uri;
}

function failure<T>(response?: Response, error?: ApiError): ImageResult<T> {
  return {ok: false, status: response?.status ?? 0, error};
}

/** Upload a prepared file and attach it to the event. */
export async function uploadPhoto(
  eventId: string,
  fileUri: string,
): Promise<ImageResult<ModImage>> {
  let file: Blob;
  try {
    file = await (await fetch(fileUri)).blob();
  } catch {
    return failure();
  }
  const slot = await fetchClient
    .POST('/v1/mod/uploads', {
      body: {contentType: 'image/jpeg', sizeBytes: file.size},
    })
    .catch(() => undefined);
  if (!slot?.data) return failure(slot?.response, slot?.error);
  // Straight to the storage: no API token on this request.
  const put = await fetch(slot.data.url, {
    method: 'PUT',
    headers: slot.data.headers,
    body: file,
  }).catch(() => undefined);
  if (!put?.ok) return failure(put);
  const attached = await fetchClient
    .POST('/v1/mod/events/{eventId}/images', {
      params: {path: {eventId}},
      body: {uploadId: slot.data.uploadId},
    })
    .catch(() => undefined);
  if (!attached?.data) return failure(attached?.response, attached?.error);
  return {ok: true, value: attached.data};
}

export const imageApi = {
  async list(eventId: string): Promise<ModImage[] | null> {
    const result = await fetchClient
      .GET('/v1/mod/events/{eventId}', {params: {path: {eventId}}})
      .catch(() => undefined);
    return result?.data?.images ?? null;
  },
  async order(
    eventId: string,
    imageIds: string[],
  ): Promise<ImageResult<ModImage[]>> {
    const result = await fetchClient
      .PUT('/v1/mod/events/{eventId}/images/order', {
        params: {path: {eventId}},
        body: {imageIds},
      })
      .catch(() => undefined);
    return result?.data
      ? {ok: true, value: result.data}
      : failure(result?.response, result?.error);
  },
  async remove(eventId: string, imageId: string): Promise<boolean> {
    const result = await fetchClient
      .DELETE('/v1/mod/events/{eventId}/images/{imageId}', {
        params: {path: {eventId, imageId}},
      })
      .catch(() => undefined);
    // Already gone counts as removed.
    return Boolean(result?.response.ok || result?.response.status === 404);
  },
  async retry(
    eventId: string,
    imageId: string,
  ): Promise<ImageResult<ModImage>> {
    const result = await fetchClient
      .POST('/v1/mod/events/{eventId}/images/{imageId}/retry', {
        params: {path: {eventId, imageId}},
      })
      .catch(() => undefined);
    return result?.data
      ? {ok: true, value: result.data}
      : failure(result?.response, result?.error);
  },
};
