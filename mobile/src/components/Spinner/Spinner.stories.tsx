import type {Meta, StoryObj} from '@storybook/react-native';

import {Spinner} from './Spinner';

const meta = {
  title: 'Basis/Spinner',
  component: Spinner,
} satisfies Meta<typeof Spinner>;

export default meta;
type Story = StoryObj<typeof meta>;

export const Default: Story = {};
export const Large: Story = {args: {size: 32}};
export const OnModerator: Story = {args: {color: '#2DD4BF'}};
