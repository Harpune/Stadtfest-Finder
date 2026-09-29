import type {Meta, StoryObj} from '@storybook/react-native';

import {EventMarker} from './EventMarker';

const meta = {
  title: 'Karte/EventMarker',
  component: EventMarker,
  args: {emoji: '🎪', color: '#FFB547'},
} satisfies Meta<typeof EventMarker>;

export default meta;
type Story = StoryObj<typeof meta>;

export const Stadtfest: Story = {};
export const Weihnachtsmarkt: Story = {args: {emoji: '🎄', color: '#5EEAD4'}};
export const Volksfest: Story = {args: {emoji: '🎡', color: '#FF6B8B'}};
