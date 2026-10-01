import type {Meta, StoryObj} from '@storybook/react-native';

import {StatusText} from './StatusText';

const meta = {
  title: 'Basis/StatusText',
  component: StatusText,
  args: {label: 'Läuft · noch 9 Tage', tone: 'running'},
} satisfies Meta<typeof StatusText>;

export default meta;
type Story = StoryObj<typeof meta>;

export const Running: Story = {};
export const Soon: Story = {args: {label: 'In 8 Tagen', tone: 'soon'}};
export const Later: Story = {args: {label: 'Ab 18. Okt', tone: 'later'}};
export const Cancelled: Story = {args: {label: 'Abgesagt', tone: 'cancelled'}};
