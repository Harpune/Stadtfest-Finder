import type {Meta, StoryObj} from '@storybook/react-native';
import React from 'react';

import {Chip} from '../Chip/Chip';
import {ChipRow} from './ChipRow';

const CATEGORIES = [
  ['🎪', 'Stadtfest', 12],
  ['🎡', 'Volksfest & Kirmes', 8],
  ['🎄', 'Weihnachtsmarkt', 9],
  ['🏰', 'Markt & Messe', 5],
] as const;

const meta = {
  title: 'Suche/ChipRow',
  component: ChipRow,
  args: {testID: 'story.row'},
} satisfies Meta<typeof ChipRow>;

export default meta;
type Story = StoryObj<typeof meta>;

export const Default: Story = {
  render: args => (
    <ChipRow {...args}>
      <Chip
        label="Alle Termine"
        dropdown
        onPress={() => undefined}
        testID="t"
      />
      {CATEGORIES.map(([emoji, name, count], i) => (
        <Chip
          key={name}
          emoji={emoji}
          label={name}
          count={count}
          active={i === 1}
          onPress={() => undefined}
          testID={`c${i}`}
        />
      ))}
    </ChipRow>
  ),
};
export const Loading: Story = {
  render: args => (
    <ChipRow {...args}>
      <Chip
        label="Alle Termine"
        dropdown
        onPress={() => undefined}
        testID="t"
      />
    </ChipRow>
  ),
};
