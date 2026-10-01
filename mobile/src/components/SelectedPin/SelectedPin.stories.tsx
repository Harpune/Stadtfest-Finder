import type {Meta, StoryObj} from '@storybook/react-native';

import {SelectedPin} from './SelectedPin';

const meta = {
  title: 'Karte/SelectedPin',
  component: SelectedPin,
  args: {
    label: 'Stadtfest Gmünd',
    dateLabel: '3.–4. Okt',
    emoji: '🎪',
    align: 'right',
  },
} satisfies Meta<typeof SelectedPin>;

export default meta;
type Story = StoryObj<typeof meta>;

export const PinRight: Story = {};
export const PinLeft: Story = {args: {align: 'left'}};
export const LongName: Story = {
  args: {label: 'Reichsstädter Tage Aalen und Umgebung'},
};
