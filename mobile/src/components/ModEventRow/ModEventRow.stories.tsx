import type {Meta, StoryObj} from '@storybook/react-native';
import {fn} from 'storybook/test';

import {ModEventRow, ModEventRowSkeleton} from './ModEventRow';

const meta = {
  title: 'Moderation/ModEventRow',
  component: ModEventRow,
  args: {
    name: 'Stadtfest Schwäbisch Gmünd',
    status: 'published',
    day: '3',
    month: 'OKT',
    meta: '🎪 Schwäbisch Gmünd · 3.–4. Okt 2026',
    favoriteCount: 86,
    onPress: fn(),
    testID: 'story.modRow',
  },
} satisfies Meta<typeof ModEventRow>;

export default meta;
type Story = StoryObj<typeof meta>;

export const Published: Story = {};
export const Draft: Story = {args: {status: 'draft', favoriteCount: 0}};
export const Cancelled: Story = {
  args: {
    name: 'Herbstmarkt Oberkochen',
    status: 'cancelled',
    favoriteCount: 23,
  },
};
export const Past: Story = {args: {status: 'past'}};
export const AutoFound: Story = {args: {status: 'draft', autoFound: true}};
export const Loading: Story = {render: () => <ModEventRowSkeleton />};
