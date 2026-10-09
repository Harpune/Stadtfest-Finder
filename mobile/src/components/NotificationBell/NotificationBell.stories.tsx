import type {Meta, StoryObj} from '@storybook/react-native';
import {View} from 'react-native';
import {fn} from 'storybook/test';

import {NotificationBell} from './NotificationBell';

const meta = {
  title: 'Benachrichtigungen/NotificationBell',
  component: NotificationBell,
  args: {unread: 3, onPress: fn(), testID: 'story.bell'},
  decorators: [
    Story => (
      <View style={{padding: 12, alignItems: 'flex-start'}}>
        <Story />
      </View>
    ),
  ],
} satisfies Meta<typeof NotificationBell>;

export default meta;
type Story = StoryObj<typeof meta>;

export const Unread: Story = {};
export const NoneUnread: Story = {args: {unread: 0}};
export const Many: Story = {args: {unread: 142}};
