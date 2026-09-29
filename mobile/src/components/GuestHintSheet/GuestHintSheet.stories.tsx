import type {Meta, StoryObj} from '@storybook/react-native';
import {fn} from 'storybook/test';

import {GuestHintSheet} from './GuestHintSheet';

const meta = {
  title: 'Konto/GuestHintSheet',
  component: GuestHintSheet,
  args: {visible: true, kind: 'favorite', onLogin: fn(), onDismiss: fn()},
  argTypes: {
    kind: {control: 'inline-radio', options: ['favorite', 'share', 'invite']},
  },
} satisfies Meta<typeof GuestHintSheet>;

export default meta;
type Story = StoryObj<typeof meta>;

export const Favorite: Story = {};
export const Share: Story = {args: {kind: 'share'}};
export const Invite: Story = {args: {kind: 'invite'}};
