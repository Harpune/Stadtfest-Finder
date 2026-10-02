import type {Meta, StoryObj} from '@storybook/react-native';
import {View} from 'react-native';
import {fn} from 'storybook/test';

import {Icon} from '../Icon/Icon';
import {ModCategoryRow} from './ModCategoryRow';

const meta = {
  title: 'Moderation/ModCategoryRow',
  component: ModCategoryRow,
  args: {
    name: 'Stadtfest',
    emoji: '🎪',
    color: '#FFB547',
    meta: '3 Feste',
    onPress: fn(),
    testID: 'story.categoryRow',
    handle: (
      <View style={{width: 32, alignItems: 'center'}}>
        <Icon name="grip" size={22} />
      </View>
    ),
  },
  decorators: [
    Story => (
      <View style={{height: 76}}>
        <Story />
      </View>
    ),
  ],
} satisfies Meta<typeof ModCategoryRow>;

export default meta;
type Story = StoryObj<typeof meta>;

export const Default: Story = {};
export const Inactive: Story = {
  args: {
    name: 'Weinfest',
    emoji: '🍷',
    color: '#C792EA',
    meta: 'Deaktiviert · 0 Feste',
    inactive: true,
  },
};
export const ReadOnly: Story = {args: {handle: undefined}};
