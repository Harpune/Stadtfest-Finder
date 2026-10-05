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
    fallback: {lat: 51.16, lon: 10.45, zoom: 4.3},
    mapStyle: offlineStyle('#15111C'),
    active: false,
    onPress: fn(),
    caption: '48.7996, 9.7986',
    testID: 'story.pinMap',
  },
} satisfies Meta<typeof PinMap>;

export default meta;
type Story = StoryObj<typeof meta>;

export const WithPin: Story = {};
export const PinMode: Story = {
  args: {active: true, caption: 'Tippe, um den Pin zu verschieben'},
};
export const Empty: Story = {args: {lat: null, lon: null, caption: undefined}};
export const ReadOnly: Story = {args: {onPress: undefined}};
export const Invalid: Story = {args: {lat: null, lon: null, invalid: true}};
