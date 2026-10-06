import type {Meta, StoryObj} from '@storybook/react-native';
import {fn} from 'storybook/test';

import {MenuRow} from './MenuRow';

const meta = {
  title: 'Basis/MenuRow',
  component: MenuRow,
  args: {label: 'Abmelden', onPress: fn(), testID: 'story.menuRow'},
} satisfies Meta<typeof MenuRow>;

export default meta;
type Story = StoryObj<typeof meta>;

export const Default: Story = {
  args: {label: 'Benachrichtigungen', chevron: true},
};
export const WithBadge: Story = {
  args: {label: 'Benachrichtigungen', chevron: true, badge: 3},
};
export const SwitchOn: Story = {
  args: {label: 'Dunkelmodus', switchValue: true, onSwitchChange: fn()},
};
export const SwitchOff: Story = {
  args: {label: 'Dunkelmodus', switchValue: false, onSwitchChange: fn()},
};
export const Moderator: Story = {
  args: {label: 'Moderator-Ansicht', tone: 'primary', chevron: true},
};
export const Logout: Story = {args: {tone: 'secondary'}};
