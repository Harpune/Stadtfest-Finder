import type {Meta, StoryObj} from '@storybook/react-native';
import {fn} from 'storybook/test';

import {SwitchRow} from './SwitchRow';

const meta = {
  title: 'Basis/SwitchRow',
  component: SwitchRow,
  args: {
    label: 'Aktiv',
    hint: 'Deaktivierte Kategorien erscheinen nicht als Chip.',
    value: true,
    onChange: fn(),
    accent: 'mod',
    testID: 'story.switchRow',
  },
} satisfies Meta<typeof SwitchRow>;

export default meta;
type Story = StoryObj<typeof meta>;

export const On: Story = {};
export const Off: Story = {args: {value: false}};
export const Disabled: Story = {args: {disabled: true}};
