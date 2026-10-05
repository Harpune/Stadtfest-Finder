import type {Meta, StoryObj} from '@storybook/react-native';
import {fn} from 'storybook/test';

import {offlineStyle} from '@/features/discover/mapStyle';

import {LocationPicker} from './LocationPicker';

const meta = {
  title: 'Moderation/LocationPicker',
  component: LocationPicker,
  args: {
    visible: true,
    start: {lat: 48.7996, lon: 9.7986},
    startZoom: 16,
    mapStyle: offlineStyle('#15111C'),
    onConfirm: fn(),
    onCancel: fn(),
    testID: 'story.locationPicker',
  },
} satisfies Meta<typeof LocationPicker>;

export default meta;
type Story = StoryObj<typeof meta>;

export const ExistingPin: Story = {};
export const OwnLocation: Story = {
  args: {start: {lat: 48.84, lon: 10.09}, startZoom: 13},
};
export const Germany: Story = {
  args: {start: {lat: 51.16, lon: 10.45}, startZoom: 5},
};
