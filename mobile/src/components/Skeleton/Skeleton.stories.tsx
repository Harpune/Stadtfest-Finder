import type {Meta, StoryObj} from '@storybook/react-native';
import React from 'react';
import {View} from 'react-native';

import {Skeleton} from './Skeleton';

const meta = {
  title: 'Basis/Skeleton',
  component: Skeleton,
  args: {height: 16},
} satisfies Meta<typeof Skeleton>;

export default meta;
type Story = StoryObj<typeof meta>;

export const Line: Story = {};
export const Image: Story = {args: {width: 84, height: 84, radius: 16}};
export const CarouselCard: Story = {
  render: () => (
    <View style={{flexDirection: 'row', gap: 12, width: 300}}>
      <Skeleton width={84} height={84} radius={16} />
      <View style={{flex: 1, gap: 8, justifyContent: 'center'}}>
        <Skeleton width="50%" height={12} />
        <Skeleton width="90%" height={18} />
        <Skeleton width="70%" height={12} />
      </View>
    </View>
  ),
};
