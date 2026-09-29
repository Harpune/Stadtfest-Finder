import type {Meta, StoryObj} from '@storybook/react-native';
import {fn} from 'storybook/test';

import {DEFAULT_FILTER, monthOptions} from '@/features/discover/filter';

import {FilterSheet} from './FilterSheet';

const CATEGORIES = [
  {id: 'c1', name: 'Stadtfest', emoji: '🎪'},
  {id: 'c2', name: 'Volksfest & Kirmes', emoji: '🎡'},
  {id: 'c3', name: 'Weihnachtsmarkt', emoji: '🎄'},
  {id: 'c4', name: 'Markt & Messe', emoji: '🏰'},
];

const meta = {
  title: 'Filter/FilterSheet',
  component: FilterSheet,
  args: {
    visible: true,
    filter: DEFAULT_FILTER,
    categories: CATEGORIES,
    monthOptions: monthOptions('2026-10-01'),
    originCaption: 'vom Standort Aalen',
    previewCount: 8,
    onDraftChange: fn(),
    onApply: fn(),
    onClose: fn(),
  },
} satisfies Meta<typeof FilterSheet>;

export default meta;
type Story = StoryObj<typeof meta>;

export const Default: Story = {};
export const Months: Story = {
  args: {
    filter: {
      ...DEFAULT_FILTER,
      time: 'months',
      months: ['2026-11', '2026-12'],
      categoryIds: ['c3'],
    },
    previewCount: 4,
  },
};
export const Loading: Story = {
  args: {previewCount: undefined, previewLoading: true},
};
export const NoResults: Story = {args: {previewCount: 0}};
export const Empty: Story = {
  args: {categories: [], originCaption: 'vom Kartenmittelpunkt'},
};
