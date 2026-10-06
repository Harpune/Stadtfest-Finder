import type {Meta, StoryObj} from '@storybook/react-native';
import {fn} from 'storybook/test';

import {NotificationRow} from './NotificationRow';

const meta = {
  title: 'Benachrichtigungen/NotificationRow',
  component: NotificationRow,
  args: {
    icon: '⏰',
    kind: 'Erinnerung',
    text: 'Reichsstädter Tage beginnt morgen: 2.–13. Okt 2026 in Aalen.',
    time: 'Heute, 9:00',
    unread: true,
    onPress: fn(),
    testID: 'story.notification',
  },
} satisfies Meta<typeof NotificationRow>;

export default meta;
type Story = StoryObj<typeof meta>;

export const Unread: Story = {};
export const Read: Story = {args: {unread: false}};
export const Cancelled: Story = {
  args: {
    icon: '⚠️',
    kind: 'Fest abgesagt',
    text: 'Herbstmarkt Oberkochen (27. Sep 2026) fällt aus. Grund: Bauarbeiten',
    time: 'Sa, 19.09.',
    tone: 'alert',
  },
};
export const LongText: Story = {
  args: {
    icon: '✏️',
    kind: 'Änderung',
    text: 'Bei Christkindlesmarkt Nürnberg haben sich Termin, Zeiten oder Ort geändert. Aktuell: 27. Nov – 24. Dez 2026 in Nürnberg.',
    time: 'Gestern',
    unread: false,
  },
};
