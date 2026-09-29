import type {Meta, StoryObj} from '@storybook/react-native';
import React from 'react';
import {View} from 'react-native';

import {CategoryPill, StatusPill} from './Pills';

const meta = {
  title: 'Detail/Pills',
  component: StatusPill,
  args: {label: 'Läuft · noch 9 Tage', tone: 'running'},
} satisfies Meta<typeof StatusPill>;

export default meta;
type Story = StoryObj<typeof meta>;

export const Running: Story = {};
export const Soon: Story = {args: {label: 'In 8 Tagen', tone: 'soon'}};
export const Later: Story = {args: {label: 'Ab 10. Okt', tone: 'later'}};
export const Cancelled: Story = {args: {label: 'Abgesagt', tone: 'cancelled'}};
export const Category: Story = {
  render: () => (
    <View style={{flexDirection: 'row', gap: 8}}>
      <CategoryPill emoji="🎡" name="Volksfest & Kirmes" />
      <StatusPill label="Läuft · noch 9 Tage" tone="running" />
    </View>
  ),
};
