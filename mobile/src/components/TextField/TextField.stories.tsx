import type {Meta, StoryObj} from '@storybook/react-native';
import {fn} from 'storybook/test';

import {TextField} from './TextField';

const meta = {
  title: 'Formular/TextField',
  component: TextField,
  args: {
    label: 'Vorname',
    value: 'Lena',
    onChangeText: fn(),
    testID: 'story.textField',
  },
} satisfies Meta<typeof TextField>;

export default meta;
type Story = StoryObj<typeof meta>;

export const Default: Story = {};
export const Empty: Story = {args: {value: ''}};
export const Error: Story = {
  args: {value: '', error: 'Bitte gib 1 bis 50 Zeichen ein.'},
};
export const Disabled: Story = {args: {disabled: true}};
export const PostalCode: Story = {
  args: {
    label: 'Postleitzahl',
    value: '73430',
    variant: 'code',
    keyboardType: 'number-pad',
    accentColor: '#2DD4BF',
  },
};
