import type {Meta, StoryObj} from '@storybook/react-native';

import {AvatarStack} from './AvatarStack';

const meta = {
  title: 'Listen/AvatarStack',
  component: AvatarStack,
  args: {
    people: [
      {id: '1', initials: 'LH'},
      {id: '2', initials: 'JW', color: '#5B7FD6'},
      {id: '3', initials: 'MS', color: '#C8508A'},
    ],
  },
} satisfies Meta<typeof AvatarStack>;

export default meta;
type Story = StoryObj<typeof meta>;

export const Default: Story = {};
export const Many: Story = {
  args: {
    people: ['LH', 'TK', 'CY', 'SB', 'AK', 'MS'].map((initials, i) => ({
      id: String(i),
      initials,
      color: ['#3E9A84', '#7B62D0', '#B07A2E', '#C85A3E', '#C8508A', '#5B7FD6'][
        i
      ],
    })),
  },
};
export const Alone: Story = {args: {people: [{id: '1', initials: 'LH'}]}};
