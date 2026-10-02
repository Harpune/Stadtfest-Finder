import {fireEvent, screen, waitFor} from '@testing-library/react-native';
import * as ImageManipulator from 'expo-image-manipulator';
import * as ImagePicker from 'expo-image-picker';
import React from 'react';

import {renderWithProviders} from '@/test-utils';

import type {ModImage} from './images';
import {ImagesSection} from './ImagesSection';

const READY = (id: string): ModImage => ({
  id,
  status: 'ready',
  position: 0,
  image: {
    url: `https://img.test/${id}/full.webp`,
    thumbUrl: `https://img.test/${id}/thumb.webp`,
  },
});

interface Call {
  method: string;
  url: string;
  body: string;
}

function mockNetwork(): Call[] {
  const calls: Call[] = [];
  jest.spyOn(global, 'fetch').mockImplementation(async (input, init) => {
    const request =
      input instanceof Request ? input : new Request(String(input), init);
    const url = request.url;
    const method = request.method;
    const body = method === 'GET' ? '' : await request.text().catch(() => '');
    calls.push({method, url, body});
    const json = (value: unknown, status = 200) =>
      new Response(JSON.stringify(value), {
        status,
        headers: {'Content-Type': 'application/json'},
      });
    if (url.startsWith('file://')) return new Response('JPEGDATA');
    if (url.endsWith('/v1/mod/uploads')) {
      return json(
        {
          uploadId: 'u1',
          url: 'https://s3.test/bucket/uploads/u1?sig=x',
          method: 'PUT',
          headers: {'Content-Type': 'image/jpeg'},
          expiresAt: '2026-10-02T10:00:00Z',
        },
        201,
      );
    }
    if (url.startsWith('https://s3.test/'))
      return new Response(null, {status: 200});
    if (url.endsWith('/v1/mod/events/e1/images')) {
      return json(
        {id: 'i2', status: 'processing', position: 1, image: null},
        201,
      );
    }
    if (url.endsWith('/images/order')) {
      return json([
        {...READY('i2'), position: 0},
        {...READY('i1'), position: 1},
      ]);
    }
    if (method === 'DELETE') return new Response(null, {status: 204});
    return json({error: 'not_found', message: ''}, 404);
  });
  return calls;
}

describe('ImagesSection', () => {
  afterEach(() => jest.restoreAllMocks());

  it('prepares, uploads with the signed URL and attaches a picked photo (R08-US1)', async () => {
    const calls = mockNetwork();
    jest.mocked(ImagePicker.launchImageLibraryAsync).mockResolvedValueOnce({
      canceled: false,
      assets: [{uri: 'file:///photo.jpg', width: 4000, height: 3000}],
    } as never);
    await renderWithProviders(
      <ImagesSection
        eventId="e1"
        images={[READY('i1')]}
        disabled={false}
        ensureEvent={async () => 'e1'}
      />,
    );

    await fireEvent.press(screen.getByTestId('mod.form.images.grid.add'));

    expect(await screen.findByText('Wird verarbeitet')).toBeOnTheScreen();
    const context = (
      ImageManipulator as unknown as {__context: {resize: jest.Mock}}
    ).__context;
    expect(context.resize).toHaveBeenCalledWith({width: 2560, height: null});
    const upload = calls.find(call => call.url.endsWith('/v1/mod/uploads'));
    expect(JSON.parse(upload?.body ?? '{}')).toEqual({
      contentType: 'image/jpeg',
      sizeBytes: 8,
    });
    expect(
      calls.some(
        c => c.method === 'PUT' && c.url.startsWith('https://s3.test/'),
      ),
    ).toBe(true);
    const attach = calls.find(c => c.url.endsWith('/v1/mod/events/e1/images'));
    expect(JSON.parse(attach?.body ?? '{}')).toEqual({uploadId: 'u1'});
  });

  it('asks for the name before the first upload of a new event', async () => {
    mockNetwork();
    jest.mocked(ImagePicker.launchImageLibraryAsync).mockResolvedValueOnce({
      canceled: false,
      assets: [{uri: 'file:///photo.jpg', width: 100, height: 100}],
    } as never);
    const ensureEvent = jest.fn(async () => null);
    await renderWithProviders(
      <ImagesSection
        eventId={null}
        images={[]}
        disabled={false}
        ensureEvent={ensureEvent}
      />,
    );

    await fireEvent.press(screen.getByTestId('mod.form.images.grid.add'));

    await waitFor(() => expect(ensureEvent).toHaveBeenCalled());
    expect(screen.queryByText('Lädt hoch')).not.toBeOnTheScreen();
  });

  it('sets another image as cover from the long-press menu (R08-US3)', async () => {
    const calls = mockNetwork();
    await renderWithProviders(
      <ImagesSection
        eventId="e1"
        images={[READY('i1'), {...READY('i2'), position: 1}]}
        disabled={false}
        ensureEvent={async () => 'e1'}
      />,
    );

    await fireEvent(
      screen.getByTestId('mod.form.images.grid.tile.1'),
      'longPress',
    );
    await fireEvent.press(
      await screen.findByTestId('mod.form.images.menu.cover'),
    );

    expect(await screen.findByText('Titelbild geändert')).toBeOnTheScreen();
    const order = calls.find(c => c.url.endsWith('/images/order'));
    expect(JSON.parse(order?.body ?? '{}')).toEqual({imageIds: ['i2', 'i1']});
  });

  it('removes an image at once', async () => {
    const calls = mockNetwork();
    await renderWithProviders(
      <ImagesSection
        eventId="e1"
        images={[READY('i1')]}
        disabled={false}
        ensureEvent={async () => 'e1'}
      />,
    );

    await fireEvent.press(
      screen.getByTestId('mod.form.images.grid.tile.0.remove'),
    );

    expect(
      screen.queryByTestId('mod.form.images.grid.tile.0'),
    ).not.toBeOnTheScreen();
    await waitFor(() =>
      expect(
        calls.some(c => c.method === 'DELETE' && c.url.endsWith('/images/i1')),
      ).toBe(true),
    );
  });
});
