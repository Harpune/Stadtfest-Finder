import type {Meta, StoryObj} from '@storybook/react-native';
import {fn} from 'storybook/test';

import {SharedListCard} from './SharedListCard';

const meta = {
  title: 'Listen/SharedListCard',
  component: SharedListCard,
  args: {
    name: 'Weihnachtsmarkt-Tour 2026',
    eventCount: 4,
    people: [
      {id: '1', initials: 'LH'},
      {id: '2', initials: 'JW', color: '#5B7FD6'},
      {id: '3', initials: 'MS', color: '#C8508A'},
    ],
    next: '🎄 Ulmer Weihnachtsmarkt · 23. Nov – 22. Dez',
    onPress: fn(),
    testID: 'story.listCard',
  },
} satisfies Meta<typeof SharedListCard>;

export default meta;
type Story = StoryObj<typeof meta>;

export const Default: Story = {};
export const WithoutEvents: Story = {
  args: {name: 'Sommerfeste 2027', eventCount: 0, next: undefined},
};
export const OnlyMe: Story = {
  args: {people: [{id: '1', initials: 'LH'}], eventCount: 1},
};
