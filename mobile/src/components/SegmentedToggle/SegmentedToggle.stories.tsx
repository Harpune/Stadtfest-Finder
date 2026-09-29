import type {Meta, StoryObj} from '@storybook/react-native';
import React, {useState} from 'react';

import {SegmentedToggle} from './SegmentedToggle';

const OPTIONS = [
  {value: 'map', label: 'Karte', icon: 'map'},
  {value: 'list', label: 'Liste', icon: 'list'},
] as const;

function Stateful({initial}: {initial: 'map' | 'list'}) {
  const [value, setValue] = useState<'map' | 'list'>(initial);
  return (
    <SegmentedToggle
      options={OPTIONS}
      value={value}
      onChange={setValue}
      testID="toggle"
    />
  );
}

const meta = {
  title: 'Basis/SegmentedToggle',
  component: Stateful,
  args: {initial: 'map'},
} satisfies Meta<typeof Stateful>;

export default meta;
type Story = StoryObj<typeof meta>;

export const Map: Story = {};
export const List: Story = {args: {initial: 'list'}};
