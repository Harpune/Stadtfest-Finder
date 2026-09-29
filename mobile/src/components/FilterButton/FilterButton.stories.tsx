import type {Meta, StoryObj} from '@storybook/react-native';
import {fn} from 'storybook/test';

import {FilterButton} from './FilterButton';

const meta = {
  title: 'Suche/FilterButton',
  component: FilterButton,
  args: {activeCount: 0, onPress: fn(), testID: 'story.filter'},
} satisfies Meta<typeof FilterButton>;

export default meta;
type Story = StoryObj<typeof meta>;

export const Default: Story = {};
export const WithActiveFilters: Story = {args: {activeCount: 2}};
