import type {Meta, StoryObj} from '@storybook/react-native';

import {LoadingPill} from './LoadingPill';

const meta = {
  title: 'Karte/LoadingPill',
  component: LoadingPill,
  args: {label: 'Feste werden geladen …'},
} satisfies Meta<typeof LoadingPill>;

export default meta;
type Story = StoryObj<typeof meta>;

export const Loading: Story = {};
export const Offline: Story = {
  args: {label: 'Offline · zuletzt geladen um 14:32', spinner: false},
};
export const ZoomHint: Story = {
  args: {label: 'Zoome hinein, um alle Feste zu sehen', spinner: false},
};
