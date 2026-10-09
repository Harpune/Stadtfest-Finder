import type {Meta, StoryObj} from '@storybook/react-native';
import {fn} from 'storybook/test';

import {EventHeaderCard} from './EventHeaderCard';

const meta = {
  title: 'Einladungen/EventHeaderCard',
  component: EventHeaderCard,
  args: {
    name: 'Oktoberfest',
    meta: '19. Sep – 4. Okt · München',
    testID: 'story.eventHeader',
  },
} satisfies Meta<typeof EventHeaderCard>;

export default meta;
type Story = StoryObj<typeof meta>;

export const Default: Story = {};
export const Pressable: Story = {args: {onPress: fn()}};
export const LongName: Story = {
  args: {
    name: 'Stadtfest Schwäbisch Gmünd',
    meta: '3.–4. Okt · Schwäbisch Gmünd',
  },
};
