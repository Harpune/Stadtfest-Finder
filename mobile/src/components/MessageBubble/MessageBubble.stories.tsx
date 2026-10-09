import type {Meta, StoryObj} from '@storybook/react-native';

import {MessageBubble} from './MessageBubble';

const meta = {
  title: 'Einladungen/MessageBubble',
  component: MessageBubble,
  args: {message: 'Samstag, 26.9., ab 11 Uhr im Schottenhamel?'},
} satisfies Meta<typeof MessageBubble>;

export default meta;
type Story = StoryObj<typeof meta>;

export const Default: Story = {};
export const Long: Story = {
  args: {
    message:
      'Samstagabend zur Coverband-Nacht? Treffpunkt 19:30 Uhr am Marktplatz. Wer mag, kommt vorher noch zum Essen mit.',
  },
};
