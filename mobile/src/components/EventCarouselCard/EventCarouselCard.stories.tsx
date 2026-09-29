import type {Meta, StoryObj} from '@storybook/react-native';
import {fn} from 'storybook/test';

import {
  EventCarouselCard,
  EventCarouselCardSkeleton,
} from './EventCarouselCard';

const meta = {
  title: 'Karten/EventCarouselCard',
  component: EventCarouselCard,
  args: {
    name: 'Oktoberfest',
    statusLabel: 'Läuft · noch 9 Tage',
    statusTone: 'running',
    dateRange: '19. Sep – 4. Okt',
    city: 'München',
    emoji: '🎡',
    distanceLabel: '133 km',
    onPress: fn(),
    testID: 'story.card',
  },
} satisfies Meta<typeof EventCarouselCard>;

export default meta;
type Story = StoryObj<typeof meta>;

export const Running: Story = {};
export const Selected: Story = {args: {selected: true}};
export const Soon: Story = {
  args: {statusLabel: 'In 8 Tagen', statusTone: 'soon'},
};
export const Cancelled: Story = {
  args: {statusLabel: 'Abgesagt', statusTone: 'cancelled'},
};
export const WithoutDistance: Story = {args: {distanceLabel: undefined}};
export const Loading: Story = {render: () => <EventCarouselCardSkeleton />};
