import React from 'react';
import {BackHandler, Text} from 'react-native';

import {renderWithProviders} from '@/test-utils';

import {BottomSheet} from './BottomSheet';

type BackListener = Parameters<typeof BackHandler.addEventListener>[1];

describe('BottomSheet', () => {
  let listeners: BackListener[];

  beforeEach(() => {
    listeners = [];
    jest
      .spyOn(BackHandler, 'addEventListener')
      .mockImplementation((_event, handler: BackListener) => {
        listeners.push(handler);
        return {
          remove: () => {
            listeners = listeners.filter(l => l !== handler);
          },
        };
      });
  });

  afterEach(() => jest.restoreAllMocks());

  /** Calls the listeners like Android does: newest first, until one returns true. */
  function pressBack(): boolean {
    return [...listeners]
      .reverse()
      .some(
        listener =>
          listener({type: 'hardwareBackPress', timeStamp: 0}) === true,
      );
  }

  function sheet(visible: boolean, onClose: () => void) {
    return (
      <BottomSheet visible={visible} onClose={onClose} testID="sheet">
        <Text>Inhalt</Text>
      </BottomSheet>
    );
  }

  it('closes on Android back instead of letting the screen go back', async () => {
    const onClose = jest.fn();
    await renderWithProviders(sheet(true, onClose));

    expect(pressBack()).toBe(true);
    expect(onClose).toHaveBeenCalledTimes(1);
  });

  it('leaves Android back to the navigator while hidden', async () => {
    const onClose = jest.fn();
    const view = await renderWithProviders(sheet(true, onClose));
    await view.rerender(sheet(false, onClose));

    expect(pressBack()).toBe(false);
    expect(onClose).not.toHaveBeenCalled();
  });
});
