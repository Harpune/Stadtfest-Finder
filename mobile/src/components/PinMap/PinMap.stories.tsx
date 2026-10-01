import type {Meta, StoryObj} from '@storybook/react-native';
import {fn} from 'storybook/test';

import {offlineStyle} from '@/features/discover/mapStyle';

import {PinMap} from './PinMap';

const meta = {
  title: 'Moderation/PinMap',
  component: PinMap,
  args: {
    lat: 48.7996,
    lon: 9.7986,
    fallback: {lat: 48.84, lon: 10.09},
    mapStyle: offlineStyle('#15111C'),
    editable: false,
    onPick: fn(),
    caption: '48.7996, 9.7986',
    testID: 'story.pinMap',
  },
} satisfies Meta<typeof PinMap>;

export default meta;
type Story = StoryObj<typeof meta>;

export const WithPin: Story = {};
export const PinMode: Story = {
  args: {editable: true, caption: 'Tippe, um den Pin zu setzen'},
};
export const Empty: Story = {args: {lat: null, lon: null, caption: undefined}};
export const Invalid: Story = {args: {lat: null, lon: null, invalid: true}};
