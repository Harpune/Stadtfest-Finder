import type {Meta, StoryObj} from '@storybook/react-native';
import {fn} from 'storybook/test';

import {ListEventRow} from './ListEventRow';

const meta = {
  title: 'Listen/ListEventRow',
  component: ListEventRow,
  args: {
    day: '23',
    month: 'NOV',
    name: 'Ulmer Weihnachtsmarkt',
    meta: '🎄 Ulm · 23. Nov – 22. Dez',
    onPress: fn(),
    testID: 'story.listEvent',
  },
} satisfies Meta<typeof ListEventRow>;

export default meta;
type Story = StoryObj<typeof meta>;

export const Default: Story = {};
export const Editing: Story = {args: {onRemove: fn()}};
export const Past: Story = {args: {past: true, day: '19', month: 'SEP'}};
export const Cancelled: Story = {args: {cancelled: true}};
