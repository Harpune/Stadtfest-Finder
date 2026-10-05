import type {Meta, StoryObj} from '@storybook/react-native';
import {fn} from 'storybook/test';

import {Button} from './Button';

const meta = {
  title: 'Basis/Button',
  component: Button,
  args: {label: 'Feste anzeigen', onPress: fn(), testID: 'story.button'},
  argTypes: {
    variant: {
      control: 'select',
      options: [
        'primary',
        'secondary',
        'ghost',
        'danger',
        'destructive',
        'mod',
        'modOutline',
      ],
    },
    size: {control: 'inline-radio', options: ['large', 'medium']},
  },
} satisfies Meta<typeof Button>;

export default meta;
type Story = StoryObj<typeof meta>;

export const Primary: Story = {};
export const Secondary: Story = {
  args: {variant: 'secondary', label: 'Einladen'},
};
export const Ghost: Story = {
  args: {variant: 'ghost', label: 'Weiter ohne Konto'},
};
export const Danger: Story = {
  args: {variant: 'danger', label: 'Liste löschen'},
};
export const Destructive: Story = {
  args: {variant: 'destructive', label: 'Endgültig löschen'},
};
export const Moderator: Story = {
  args: {variant: 'mod', label: 'Veröffentlichen'},
};
export const ModeratorOutline: Story = {
  args: {variant: 'modOutline', label: 'Suchen', size: 'medium'},
};
export const Loading: Story = {args: {loading: true, label: 'Anmelden'}};
export const Disabled: Story = {
  args: {disabled: true, label: 'Einladung senden (0)'},
};
