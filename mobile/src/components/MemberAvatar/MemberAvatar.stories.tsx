import type {Meta, StoryObj} from '@storybook/react-native';
import {fn} from 'storybook/test';

import {MemberAvatar} from './MemberAvatar';

const meta = {
  title: 'Listen/MemberAvatar',
  component: MemberAvatar,
  args: {
    initials: 'JW',
    color: '#5B7FD6',
    label: 'Jonas',
    testID: 'story.member',
  },
} satisfies Meta<typeof MemberAvatar>;

export default meta;
type Story = StoryObj<typeof meta>;

export const Default: Story = {};
export const Me: Story = {
  args: {initials: 'LH', color: undefined, label: 'Du'},
};
export const Removable: Story = {args: {onRemove: fn()}};
