import type {Meta, StoryObj} from '@storybook/react-native';

import {Avatar} from './Avatar';

const meta = {
  title: 'Profil/Avatar',
  component: Avatar,
  args: {initials: 'LH'},
} satisfies Meta<typeof Avatar>;

export default meta;
type Story = StoryObj<typeof meta>;

export const Default: Story = {};
export const Large: Story = {args: {size: 64}};
export const WithoutName: Story = {args: {initials: undefined}};
