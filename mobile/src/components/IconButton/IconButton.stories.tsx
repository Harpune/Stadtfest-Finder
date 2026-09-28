import type {Meta, StoryObj} from '@storybook/react-native';
import React from 'react';
import {fn} from 'storybook/test';

import {Text} from '../Text/Text';
import {IconButton} from './IconButton';

const meta = {
  title: 'Basis/IconButton',
  component: IconButton,
  args: {
    icon: <Text>♥</Text>,
    accessibilityLabel: 'Favorit',
    onPress: fn(),
    testID: 'story.iconButton',
  },
} satisfies Meta<typeof IconButton>;

export default meta;
type Story = StoryObj<typeof meta>;

export const Glass: Story = {};
export const Surface: Story = {args: {variant: 'surface'}};
export const Disabled: Story = {args: {disabled: true}};
