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
    value: 150,
    onChange: fn(),
    min: 10,
    max: 300,
    step: 10,
    caption: 'vom Standort Aalen',
    testID: 'story.radius',
  },
  render: args => <Stateful {...args} />,
} satisfies Meta<typeof RangeSlider>;

export default meta;
type Story = StoryObj<typeof meta>;

export const Default: Story = {};
export const MapCenter: Story = {
  args: {caption: 'vom Kartenmittelpunkt', value: 10},
};
export const Disabled: Story = {args: {disabled: true}};
