import type {Meta, StoryObj} from '@storybook/react-native';

import {ImagePlaceholder} from './ImagePlaceholder';

const meta = {
  title: 'Basis/ImagePlaceholder',
  component: ImagePlaceholder,
  args: {label: 'Foto', style: {width: 84, height: 84}, radius: 14},
} satisfies Meta<typeof ImagePlaceholder>;

export default meta;
type Story = StoryObj<typeof meta>;

export const Thumb: Story = {};
export const Cover: Story = {
  args: {label: 'Festfoto', style: {height: 160}, radius: 0},
};
