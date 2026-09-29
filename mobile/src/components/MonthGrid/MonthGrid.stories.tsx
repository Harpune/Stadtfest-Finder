import type {Meta, StoryObj} from '@storybook/react-native';
import React, {useState} from 'react';
import {fn} from 'storybook/test';

import {monthOptions} from '@/features/discover/filter';

import {MonthGrid, MonthGridProps} from './MonthGrid';

const OPTIONS = monthOptions('2026-10-01');

function Stateful(props: MonthGridProps) {
  const [selected, setSelected] = useState<string[]>([...props.selected]);
  return (
    <MonthGrid
      {...props}
      selected={selected}
      onToggle={v =>
        setSelected(s => (s.includes(v) ? s.filter(x => x !== v) : [...s, v]))
      }
    />
  );
}

const meta = {
  title: 'Filter/MonthGrid',
  component: MonthGrid,
  args: {
    options: OPTIONS,
    selected: [],
    onToggle: fn(),
    testID: 'story.months',
  },
  render: args => <Stateful {...args} />,
} satisfies Meta<typeof MonthGrid>;

export default meta;
type Story = StoryObj<typeof meta>;

export const Default: Story = {};
export const Selected: Story = {args: {selected: ['2026-11', '2026-12']}};
