import type {Meta, StoryObj} from '@storybook/react-native';
import {fn} from 'storybook/test';

import {ListsTeaser} from './ListsTeaser';

const meta = {
  title: 'Listen/ListsTeaser',
  component: ListsTeaser,
  args: {
    people: [
      {id: '1', initials: 'JW', color: '#5B7FD6'},
      {id: '2', initials: 'MS', color: '#C8508A'},
      {id: '3', initials: 'TK', color: '#3E9A84'},
    ],
    summary:
      '3 Listen · Weihnachtsmarkt-Tour 2026, Wiesn-Crew, Familienausflüge',
    onPress: fn(),
    testID: 'story.listsTeaser',
  },
} satisfies Meta<typeof ListsTeaser>;

export default meta;
type Story = StoryObj<typeof meta>;

export const Default: Story = {};
export const Empty: Story = {
  args: {people: [], summary: 'Plane Festbesuche mit Freunden'},
};
