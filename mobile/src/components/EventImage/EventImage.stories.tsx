import type {Meta, StoryObj} from '@storybook/react-native';
import {Image} from 'react-native';

import {EventImage} from './EventImage';

// Bundled asset instead of a remote URL: stories never load third-party hosts.
const SAMPLE = Image.resolveAssetSource(
  require('../../../assets/splash-icon.png') as number,
).uri;

const meta = {
  title: 'Basis/EventImage',
  component: EventImage,
  args: {
    uri: SAMPLE,
    label: 'Festfoto',
    style: {height: 160},
    radius: 18,
    testID: 'story.eventImage',
  },
} satisfies Meta<typeof EventImage>;

export default meta;
type Story = StoryObj<typeof meta>;

export const Loaded: Story = {};
export const WithoutImage: Story = {args: {uri: null}};
export const Broken: Story = {args: {uri: 'https://invalid.example/x.webp'}};
