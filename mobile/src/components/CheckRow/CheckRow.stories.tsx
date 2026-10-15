import type {Meta, StoryObj} from '@storybook/react-native';
import {fn} from 'storybook/test';

import {Avatar} from '../Avatar/Avatar';
import {CheckRow} from './CheckRow';

const meta = {
  title: 'Basis/CheckRow',
  component: CheckRow,
  args: {
    label: 'Jonas Weber',
    lead: <Avatar initials="JW" color="#5B7FD6" size={40} />,
    checked: false,
    onPress: fn(),
    testID: 'story.check',
  },
} satisfies Meta<typeof CheckRow>;

export default meta;
type Story = StoryObj<typeof meta>;

export const Unchecked: Story = {};
export const Checked: Story = {args: {checked: true}};
export const WithMeta: Story = {
  args: {
    label: 'Ulmer Weihnachtsmarkt',
    meta: '23. Nov – 22. Dez · Ulm',
    lead: undefined,
  },
};
export const Disabled: Story = {args: {disabled: true}};
