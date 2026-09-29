import type {Meta, StoryObj} from '@storybook/react-native';
import {fn} from 'storybook/test';

import {Chip} from './Chip';

const meta = {
  title: 'Suche/Chip',
  component: Chip,
  args: {
    label: 'Stadtfest',
    emoji: '🎪',
    count: 12,
    onPress: fn(),
    testID: 'story.chip',
  },
  argTypes: {
    variant: {control: 'inline-radio', options: ['floating', 'sheet']},
  },
} satisfies Meta<typeof Chip>;

export default meta;
type Story = StoryObj<typeof meta>;

export const Default: Story = {};
export const Active: Story = {args: {active: true}};
export const TimeDropdown: Story = {
  args: {
    label: 'Alle Termine',
    emoji: undefined,
    count: undefined,
    dropdown: true,
  },
};
export const Sheet: Story = {args: {variant: 'sheet', count: undefined}};
export const SheetActive: Story = {
  args: {variant: 'sheet', count: undefined, active: true},
};
export const Empty: Story = {args: {count: 0}};
export const Disabled: Story = {args: {disabled: true}};
