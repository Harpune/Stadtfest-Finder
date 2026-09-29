import type {Meta, StoryObj} from '@storybook/react-native';

import {ClusterMarker} from './ClusterMarker';

const meta = {
  title: 'Karte/ClusterMarker',
  component: ClusterMarker,
  args: {count: 3},
} satisfies Meta<typeof ClusterMarker>;

export default meta;
type Story = StoryObj<typeof meta>;

export const Small: Story = {};
export const Large: Story = {args: {count: 128}};
