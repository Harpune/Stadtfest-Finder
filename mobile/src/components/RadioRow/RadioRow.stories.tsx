import type {Meta, StoryObj} from '@storybook/react-native';
import {fn} from 'storybook/test';

import {RadioRow} from './RadioRow';

const meta = {
  title: 'Basis/RadioRow',
  component: RadioRow,
  args: {
    label: 'Stadtfest',
    emoji: '🎪',
    selected: false,
    onPress: fn(),
    testID: 'story.radioRow',
  },
} satisfies Meta<typeof RadioRow>;

export default meta;
type Story = StoryObj<typeof meta>;

export const Default: Story = {};
export const Selected: Story = {args: {selected: true}};
export const Disabled: Story = {args: {disabled: true}};
