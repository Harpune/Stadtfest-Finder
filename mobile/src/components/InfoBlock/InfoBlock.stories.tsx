import type {Meta, StoryObj} from '@storybook/react-native';

import {InfoBlock} from './InfoBlock';

const meta = {
  title: 'Detail/InfoBlock',
  component: InfoBlock,
  args: {
    rows: [
      {
        icon: 'calendar',
        label: 'Zeitraum',
        lines: ['19. September – 4. Oktober 2026'],
      },
      {
        icon: 'clock',
        label: 'Öffnungszeiten',
        lines: ['Mo–Fr 10–23:30 Uhr', 'Sa, So & Feiertag 9–23:30 Uhr'],
      },
      {
        icon: 'ticket',
        label: 'Eintritt',
        lines: ['Frei · Fahrgeschäfte kostenpflichtig'],
      },
    ],
  },
} satisfies Meta<typeof InfoBlock>;

export default meta;
type Story = StoryObj<typeof meta>;

export const Default: Story = {};
export const Loading: Story = {
  args: {
    rows: [
      {
        icon: 'calendar',
        label: 'Zeitraum',
        lines: ['19. September – 4. Oktober 2026'],
      },
    ],
    loading: true,
  },
};
