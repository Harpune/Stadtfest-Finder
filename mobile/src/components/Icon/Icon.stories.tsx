import type {Meta, StoryObj} from '@storybook/react-native';
import React from 'react';
import {View} from 'react-native';

import {Icon, IconName} from './Icon';

const NAMES: IconName[] = [
  'search',
  'sliders',
  'close',
  'plus',
  'minus',
  'locate',
  'map',
  'list',
  'heart',
  'user',
  'chevronDown',
];

const meta = {
  title: 'Basis/Icon',
  component: Icon,
  args: {name: 'search'},
  argTypes: {name: {control: 'select', options: NAMES}},
} satisfies Meta<typeof Icon>;

export default meta;
type Story = StoryObj<typeof meta>;

export const Default: Story = {};
export const All: Story = {
  render: () => (
    <View style={{flexDirection: 'row', flexWrap: 'wrap', gap: 16}}>
      {NAMES.map(name => (
        <Icon key={name} name={name} />
      ))}
    </View>
  ),
};
