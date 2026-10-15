import type {Meta, StoryObj} from '@storybook/react-native';
import {fn} from 'storybook/test';

import {InvitationEventCard} from './InvitationEventCard';

const meta = {
  title: 'Einladungen/InvitationEventCard',
  component: InvitationEventCard,
  args: {
    name: 'Stadtfest Schwäbisch Gmünd',
    when: 'In 8 Tagen',
    meta: '3.–4. Okt · Schwäbisch Gmünd',
    imageLabel: 'Festfoto',
    onPress: fn(),
    testID: 'story.invitationEvent',
  },
} satisfies Meta<typeof InvitationEventCard>;

export default meta;
type Story = StoryObj<typeof meta>;

export const Default: Story = {};
export const Running: Story = {args: {when: 'Läuft gerade'}};
