import type {Meta, StoryObj} from '@storybook/react-native';
import {fn} from 'storybook/test';

import {ComingAlongHint} from './ComingAlongHint';

const meta = {
  title: 'Einladungen/ComingAlongHint',
  component: ComingAlongHint,
  args: {
    people: [
      {id: 'jw', initials: 'JW', color: '#5B7FD6'},
      {id: 'tk', initials: 'TK', color: '#3E9C87'},
    ],
    text: 'Jonas und Tim kommen mit',
    onPress: fn(),
    testID: 'story.comingAlong',
  },
} satisfies Meta<typeof ComingAlongHint>;

export default meta;
type Story = StoryObj<typeof meta>;

export const Default: Story = {};
export const One: Story = {
  args: {
    people: [{id: 'jw', initials: 'JW', color: '#5B7FD6'}],
    text: 'Jonas kommt mit',
  },
};
export const Many: Story = {
  args: {
    people: [
      {id: 'jw', initials: 'JW', color: '#5B7FD6'},
      {id: 'tk', initials: 'TK', color: '#3E9C87'},
      {id: 'ms', initials: 'MS', color: '#C8508A'},
      {id: 'cy', initials: 'CY', color: '#7C5BD6'},
    ],
    text: 'Jonas, Tim und 2 weitere kommen mit',
  },
};
