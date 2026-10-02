import {fireEvent, screen} from '@testing-library/react-native';
import React from 'react';

import {renderWithProviders} from '@/test-utils';

import {ImageGrid, type ImageTile} from './ImageGrid';

async function renderGrid(tiles: ImageTile[], canAdd = true) {
  const handlers = {
    onAdd: jest.fn(),
    onRemove: jest.fn(),
    onRetry: jest.fn(),
    onLongPress: jest.fn(),
  };
  const view = await renderWithProviders(
    <ImageGrid tiles={tiles} canAdd={canAdd} testID="grid" {...handlers} />,
  );
  return {view, ...handlers};
}

describe('ImageGrid', () => {
  it('labels the first ready image as cover', async () => {
    await renderGrid([
      {key: 'a', state: 'ready', uri: 'https://img.test/a.webp'},
      {key: 'b', state: 'ready', uri: 'https://img.test/b.webp'},
    ]);
    expect(screen.getAllByText('Titelbild')).toHaveLength(1);
  });

  it('shows uploading and processing tiles without a remove button while uploading', async () => {
    await renderGrid([
      {key: 'a', state: 'uploading', uri: 'file:///a.jpg'},
      {key: 'b', state: 'processing'},
    ]);
    expect(screen.getByText('Lädt hoch')).toBeOnTheScreen();
    expect(screen.getByText('Wird verarbeitet')).toBeOnTheScreen();
    expect(screen.queryByTestId('grid.tile.0.remove')).not.toBeOnTheScreen();
    expect(screen.getByTestId('grid.tile.1.remove')).toBeOnTheScreen();
  });

  it('offers retry on failed images', async () => {
    const {onRetry} = await renderGrid([{key: 'a', state: 'failed'}]);
    await fireEvent.press(screen.getByTestId('grid.tile.0.retry'));
    expect(onRetry).toHaveBeenCalledWith('a');
  });

  it('removes, adds and opens the menu by long press', async () => {
    const {onRemove, onAdd, onLongPress} = await renderGrid([
      {key: 'a', state: 'ready', uri: 'https://img.test/a.webp'},
    ]);
    await fireEvent.press(screen.getByTestId('grid.tile.0.remove'));
    await fireEvent(screen.getByTestId('grid.tile.0'), 'longPress');
    await fireEvent.press(screen.getByTestId('grid.add'));
    expect(onRemove).toHaveBeenCalledWith('a');
    expect(onLongPress).toHaveBeenCalledWith('a');
    expect(onAdd).toHaveBeenCalled();
  });

  it('hides the add tile when full', async () => {
    await renderGrid([], false);
    expect(screen.queryByTestId('grid.add')).not.toBeOnTheScreen();
  });
});
