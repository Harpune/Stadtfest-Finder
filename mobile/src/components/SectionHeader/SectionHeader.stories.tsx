import type {Meta, StoryObj} from '@storybook/react-native';

import {SectionHeader} from './SectionHeader';

const meta = {
  title: 'Detail/SectionHeader',
  component: SectionHeader,
  args: {title: 'Programm & Highlights'},
} satisfies Meta<typeof SectionHeader>;

export default meta;
type Story = StoryObj<typeof meta>;

export const Default: Story = {};
