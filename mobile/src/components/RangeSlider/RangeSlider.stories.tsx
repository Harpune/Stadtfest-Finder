import type {Meta, StoryObj} from '@storybook/react-native';
import React, {useState} from 'react';
import {fn} from 'storybook/test';

import {RangeSlider, RangeSliderProps} from './RangeSlider';

function Stateful(props: RangeSliderProps) {
  const [value, setValue] = useState(props.value);
  return <RangeSlider {...props} value={value} onChange={setValue} />;
}

const meta = {
  title: 'Filter/RangeSlider',
  component: RangeSlider,
  args: {
    label: 'Radius',
    formatValue: (v: number) => `bis ${v} km`,
    unit: 'km',
    value: 25,
    onChange: fn(),
    min: 5,
    max: 150,
    step: 5,
    caption: 'um Aalen',
    testID: 'story.radius',
  },
  render: args => <Stateful {...args} />,
} satisfies Meta<typeof RangeSlider>;

export default meta;
type Story = StoryObj<typeof meta>;

export const Default: Story = {};
export const Minimum: Story = {args: {value: 5}};
export const Disabled: Story = {args: {disabled: true}};
