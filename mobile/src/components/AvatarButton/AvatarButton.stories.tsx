import type {Meta, StoryObj} from '@storybook/react-native';
import {fn} from 'storybook/test';

import {AvatarButton} from './AvatarButton';

const meta = {
  title: 'Profil/AvatarButton',
  component: AvatarButton,
  args: {onPress: fn(), testID: 'story.avatar'},
} satisfies Meta<typeof AvatarButton>;

export default meta;
type Story = StoryObj<typeof meta>;

export const Guest: Story = {};
export const SignedIn: Story = {args: {initials: 'LH'}};
export const Unread: Story = {args: {initials: 'LH', hasUnread: true}};
