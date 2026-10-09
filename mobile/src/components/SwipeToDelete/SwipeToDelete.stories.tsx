import type {Meta, StoryObj} from '@storybook/react-native';
import {fn} from 'storybook/test';

import {NotificationRow} from '../NotificationRow/NotificationRow';
import {SwipeToDelete} from './SwipeToDelete';

const meta = {
  title: 'Basis/SwipeToDelete',
  component: SwipeToDelete,
  args: {
    label: 'Löschen',
    onDelete: fn(),
    testID: 'story.swipe',
    children: (
      <NotificationRow
        icon="⏰"
        kind="Erinnerung"
        text="Nach links wischen zum Löschen."
        time="Heute, 9:00"
        unread
        onPress={fn()}
        testID="story.swipe.row"
      />
    ),
  },
} satisfies Meta<typeof SwipeToDelete>;

export default meta;
type Story = StoryObj<typeof meta>;

export const Default: Story = {};
export const ReadRow: Story = {
  args: {
    children: (
      <NotificationRow
        icon="⚠️"
        kind="Fest abgesagt"
        text="Herbstmarkt Oberkochen (27. Sep 2026) fällt aus."
        time="Sa, 19.09."
        unread={false}
        tone="alert"
        onPress={fn()}
        testID="story.swipe.row"
      />
    ),
  },
};
