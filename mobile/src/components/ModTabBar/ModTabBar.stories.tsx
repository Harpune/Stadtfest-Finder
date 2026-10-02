import type {Meta, StoryObj} from '@storybook/react-native';
import {fn} from 'storybook/test';

import {ModTabBar} from './ModTabBar';

const TABS = [
  {key: 'events', label: 'Feste', emoji: '📅'},
  {key: 'categories', label: 'Kategorien', emoji: '🏷️'},
] as const;

const meta = {
  title: 'Moderation/ModTabBar',
  component: ModTabBar<'events' | 'categories'>,
  args: {
    tabs: TABS,
    active: 'events',
    onSelect: fn(),
    bottomInset: 0,
    testID: 'story.modTabs',
  },
} satisfies Meta<typeof ModTabBar<'events' | 'categories'>>;

export default meta;
type Story = StoryObj<typeof meta>;

export const Events: Story = {};
export const Categories: Story = {args: {active: 'categories'}};
