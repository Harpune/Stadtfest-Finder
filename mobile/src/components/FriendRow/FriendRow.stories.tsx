import type {Meta, StoryObj} from '@storybook/react-native';

import {FriendRow} from './FriendRow';

const meta = {
  title: 'Freunde/FriendRow',
  component: FriendRow,
  args: {
    name: 'Tim Krause',
    initials: 'TK',
    color: '#5B7FD6',
    meta: 'Befreundet seit Okt 2026',
    testID: 'story.friend',
  },
} satisfies Meta<typeof FriendRow>;

export default meta;
type Story = StoryObj<typeof meta>;

export const Default: Story = {};
export const LongName: Story = {
  args: {
    name: 'Maximiliane von Hohenlohe-Langenburg',
    initials: 'MV',
    color: '#C8508A',
  },
};
export const WithoutLastName: Story = {
  args: {name: 'Apple-Nutzer', initials: 'A', color: '#3E9A84'},
};
