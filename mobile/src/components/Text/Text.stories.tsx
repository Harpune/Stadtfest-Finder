import type {Meta, StoryObj} from '@storybook/react-native';

import {Text} from './Text';

const meta = {
  title: 'Basis/Text',
  component: Text,
  args: {children: 'Reichsstädter Tage', variant: 'displayL'},
  argTypes: {
    variant: {
      control: 'select',
      options: [
        'displayXL',
        'displayL',
        'displayM',
        'displayS',
        'body',
        'bodyStrong',
        'meta',
        'caption',
        'label',
        'micro',
      ],
    },
    tone: {
      control: 'select',
      options: [
        'default',
        'muted',
        'faint',
        'primary',
        'secondary',
        'error',
        'mod',
      ],
    },
  },
} satisfies Meta<typeof Text>;

export default meta;
type Story = StoryObj<typeof meta>;

export const Display: Story = {};
export const Body: Story = {
  args: {
    variant: 'body',
    children: 'Das größte Fest der Ostalb mit Umzug, Musik und Fahrgeschäften.',
  },
};
export const SectionLabel: Story = {
  args: {variant: 'label', children: 'Zeitraum'},
};
export const Running: Story = {
  args: {variant: 'meta', tone: 'primary', children: '● Läuft · noch 9 Tage'},
};
export const Countdown: Story = {
  args: {variant: 'meta', tone: 'secondary', children: 'In 8 Tagen'},
};
export const Error: Story = {
  args: {
    variant: 'caption',
    tone: 'error',
    children: 'Bitte gib einen Namen ein.',
  },
};
