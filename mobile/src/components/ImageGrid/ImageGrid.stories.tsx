import type {Meta, StoryObj} from '@storybook/react-native';
import {Image} from 'react-native';
import {fn} from 'storybook/test';

import {ImageGrid} from './ImageGrid';

// Bundled asset instead of a remote URL: stories never load third-party hosts.
const SAMPLE = Image.resolveAssetSource(
  require('../../../assets/splash-icon.png') as number,
).uri;

const meta = {
  title: 'Moderation/ImageGrid',
  component: ImageGrid,
  args: {
    tiles: [
      {key: 'a', state: 'ready', uri: SAMPLE},
      {key: 'b', state: 'ready', uri: SAMPLE},
    ],
    canAdd: true,
    onAdd: fn(),
    onRemove: fn(),
    onRetry: fn(),
    onLongPress: fn(),
    testID: 'story.imageGrid',
  },
} satisfies Meta<typeof ImageGrid>;

export default meta;
type Story = StoryObj<typeof meta>;

export const Default: Story = {};
export const Empty: Story = {args: {tiles: []}};
export const Loading: Story = {
  args: {
    tiles: [
      {key: 'a', state: 'ready', uri: SAMPLE},
      {key: 'b', state: 'uploading', uri: SAMPLE},
      {key: 'c', state: 'processing'},
    ],
  },
};
export const Error: Story = {
  args: {
    tiles: [
      {key: 'a', state: 'ready', uri: SAMPLE},
      {key: 'b', state: 'failed'},
    ],
  },
};
export const Full: Story = {args: {canAdd: false}};
export const Disabled: Story = {args: {disabled: true}};
