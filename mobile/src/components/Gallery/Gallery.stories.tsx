import type {Meta, StoryObj} from '@storybook/react-native';

import {Gallery} from './Gallery';

const meta = {
  title: 'Detail/Gallery',
  component: Gallery,
  args: {images: [], name: 'Oktoberfest'},
} satisfies Meta<typeof Gallery>;

export default meta;
type Story = StoryObj<typeof meta>;

export const Placeholder: Story = {};
export const WithImages: Story = {
  args: {
    images: [
      {url: 'https://picsum.photos/id/1016/800/600'},
      {url: 'https://picsum.photos/id/1018/800/600'},
      {url: 'https://picsum.photos/id/1025/800/600'},
    ],
  },
};
