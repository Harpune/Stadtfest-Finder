import type {Meta, StoryObj} from '@storybook/react-native';
import {fn} from 'storybook/test';

import {FavoriteButton} from './FavoriteButton';

const meta = {
  title: 'Basis/FavoriteButton',
  component: FavoriteButton,
  args: {
    active: false,
    accessibilityLabel: 'Oktoberfest merken',
    onPress: fn(),
    testID: 'story.favorite',
  },
} satisfies Meta<typeof FavoriteButton>;

export default meta;
type Story = StoryObj<typeof meta>;

export const Default: Story = {};
export const Active: Story = {args: {active: true}};
export const Small: Story = {args: {size: 40, iconSize: 20}};
export const Disabled: Story = {args: {disabled: true}};
