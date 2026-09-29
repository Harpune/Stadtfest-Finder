import type {Meta, StoryObj} from '@storybook/react-native';
import {fn} from 'storybook/test';

import {EventListCard, EventListCardSkeleton} from './EventListCard';

const meta = {
  title: 'Karten/EventListCard',
  component: EventListCard,
  args: {
    name: 'Oktoberfest',
    statusLabel: 'Läuft · noch 9 Tage',
    statusTone: 'running',
    dateRange: '19. Sep – 4. Okt',
    city: 'München',
    categoryName: 'Volksfest & Kirmes',
    emoji: '🎡',
    distanceLabel: '133 km',
    onPress: fn(),
    onFavoritePress: fn(),
    testID: 'story.listcard',
  },
} satisfies Meta<typeof EventListCard>;

export default meta;
type Story = StoryObj<typeof meta>;

export const Running: Story = {};
export const Cancelled: Story = {
  args: {
    name: 'Herbstmarkt Oberkochen',
    statusLabel: 'Abgesagt',
    statusTone: 'cancelled',
  },
};
export const Later: Story = {
  args: {statusLabel: 'Ab 10. Okt', statusTone: 'later'},
};
export const Loading: Story = {render: () => <EventListCardSkeleton />};
