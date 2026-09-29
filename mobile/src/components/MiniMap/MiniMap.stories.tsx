import type {Meta, StoryObj} from '@storybook/react-native';
import {fn} from 'storybook/test';

import {offlineStyle} from '@/features/discover/mapStyle';

import {MiniMap} from './MiniMap';

const meta = {
  title: 'Detail/MiniMap',
  component: MiniMap,
  args: {
    lat: 48.8368,
    lon: 10.0932,
    emoji: '🎪',
    mapStyle: offlineStyle('#231C30'),
    onPress: fn(),
  },
} satisfies Meta<typeof MiniMap>;

export default meta;
type Story = StoryObj<typeof meta>;

export const Offline: Story = {};
