import type {Meta, StoryObj} from '@storybook/react-native';

import {ProgramList} from './ProgramList';

const meta = {
  title: 'Detail/ProgramList',
  component: ProgramList,
  args: {
    entries: [
      {
        key: '1',
        weekday: 'SA',
        day: '19.9.',
        title: 'Einzug der Wiesnwirte',
        subtitle: '10:45 Uhr · danach Anstich um 12 Uhr',
      },
      {
        key: '2',
        weekday: 'SO',
        day: '20.9.',
        title: 'Trachten- und Schützenzug',
        subtitle: '10 Uhr · Innenstadt',
      },
      {
        key: '3',
        weekday: 'SO',
        day: '4.10.',
        title: 'Böllerschießen an der Bavaria',
      },
    ],
  },
} satisfies Meta<typeof ProgramList>;

export default meta;
type Story = StoryObj<typeof meta>;

export const Default: Story = {};
export const Empty: Story = {args: {entries: []}};
