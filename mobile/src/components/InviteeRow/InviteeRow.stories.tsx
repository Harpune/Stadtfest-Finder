import type {Meta, StoryObj} from '@storybook/react-native';

import {InviteeRow} from './InviteeRow';

const meta = {
  title: 'Einladungen/InviteeRow',
  component: InviteeRow,
  args: {
    name: 'Jonas Weber',
    initials: 'JW',
    color: '#5B7FD6',
    meta: 'hat zugesagt',
    status: 'accepted',
    testID: 'story.invitee',
  },
} satisfies Meta<typeof InviteeRow>;

export default meta;
type Story = StoryObj<typeof meta>;

export const Accepted: Story = {};
export const Open: Story = {
  args: {
    name: 'Can Yilmaz',
    initials: 'CY',
    meta: 'Eingeladen vor 2 Tagen',
    status: 'open',
  },
};
export const Declined: Story = {
  args: {
    name: 'Mia Schulz',
    initials: 'MS',
    meta: 'hat abgesagt',
    status: 'declined',
  },
};
export const Compact: Story = {args: {meta: undefined}};
export const Me: Story = {
  args: {name: 'Du', initials: 'LH', color: undefined, meta: 'Lädt ein'},
};
