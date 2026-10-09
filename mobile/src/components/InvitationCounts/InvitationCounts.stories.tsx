import type {Meta, StoryObj} from '@storybook/react-native';

import {InvitationCounts} from './InvitationCounts';

const meta = {
  title: 'Einladungen/InvitationCounts',
  component: InvitationCounts,
  args: {coming: 3, open: 1, declined: 1, testID: 'story.counts'},
} satisfies Meta<typeof InvitationCounts>;

export default meta;
type Story = StoryObj<typeof meta>;

export const Default: Story = {};
export const OnlyHost: Story = {args: {coming: 1, open: 4, declined: 0}};
