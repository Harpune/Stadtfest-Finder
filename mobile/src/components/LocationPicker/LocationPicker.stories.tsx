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
    exact: true,
    mapStyle: offlineStyle('#15111C'),
    onConfirm: fn(),
    onCancel: fn(),
    testID: 'story.locationPicker',
  },
} satisfies Meta<typeof LocationPicker>;

export default meta;
type Story = StoryObj<typeof meta>;

export const ExistingPin: Story = {};
export const RegionStart: Story = {
  args: {start: {lat: 48.84, lon: 10.09}, exact: false},
};
