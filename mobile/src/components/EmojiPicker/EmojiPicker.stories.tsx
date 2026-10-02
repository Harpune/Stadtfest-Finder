import type {Meta, StoryObj} from '@storybook/react-native';
import {fn} from 'storybook/test';

import {EmojiPicker} from './EmojiPicker';

const meta = {
  title: 'Moderation/EmojiPicker',
  component: EmojiPicker,
  args: {
    options: [
      '🎪',
      '🎡',
      '🎄',
      '🐎',
      '🍺',
      '🍷',
      '🎭',
      '🎶',
      '🏰',
      '🎃',
      '🌸',
      '🔥',
    ],
    value: '🎄',
    onChange: fn(),
    testID: 'story.emojiPicker',
  },
} satisfies Meta<typeof EmojiPicker>;

export default meta;
type Story = StoryObj<typeof meta>;

export const Default: Story = {};
export const Disabled: Story = {args: {disabled: true}};
