import type {Meta, StoryObj} from '@storybook/react-native';
import {fn} from 'storybook/test';

import {MapControls} from './MapControls';

const meta = {
  title: 'Karte/MapControls',
  component: MapControls,
  args: {onZoomIn: fn(), onZoomOut: fn(), onLocate: fn()},
} satisfies Meta<typeof MapControls>;

export default meta;
type Story = StoryObj<typeof meta>;

export const Default: Story = {};
export const WithoutLocation: Story = {args: {onLocate: undefined}};
export const MaxZoom: Story = {args: {zoomInDisabled: true}};
