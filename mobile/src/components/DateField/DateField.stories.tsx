import type {Meta, StoryObj} from '@storybook/react-native';
import {fn} from 'storybook/test';

import {DateField} from './DateField';

const meta = {
  title: 'Basis/DateField',
  component: DateField,
  args: {
    label: 'Beginn',
    value: '2026-10-03',
    onChange: fn(),
    placeholder: 'tt.mm.jjjj',
    testID: 'story.date',
  },
} satisfies Meta<typeof DateField>;

export default meta;
type Story = StoryObj<typeof meta>;

export const Filled: Story = {};
export const Empty: Story = {args: {value: null}};
export const Invalid: Story = {args: {value: null, invalid: true}};
