import type {Meta, StoryObj} from '@storybook/react-native';
import {fn} from 'storybook/test';

import {EmptyState} from './EmptyState';

const meta = {
  title: 'Zustände/EmptyState',
  component: EmptyState,
  args: {
    title: 'Keine Feste im Umkreis',
    text: 'Im Umkreis von 10 km gibt es mit diesen Filtern gerade nichts. Erweitere den Umkreis oder setze die Filter zurück.',
    primary: {label: 'Umkreis auf 300 km', onPress: fn(), testID: 'a'},
    secondary: {label: 'Filter zurücksetzen', onPress: fn(), testID: 'b'},
    testID: 'story.empty',
  },
} satisfies Meta<typeof EmptyState>;

export default meta;
type Story = StoryObj<typeof meta>;

export const NoEventsInRadius: Story = {};
export const SearchWithoutResults: Story = {
  args: {
    title: 'Kein Fest für „Reichsstätter“',
    text: 'Prüfe die Schreibweise oder suche nach einer Stadt.',
    primary: undefined,
  },
};
export const Error: Story = {
  args: {
    title: 'Feste konnten nicht geladen werden',
    text: 'Prüfe deine Verbindung.',
    primary: {label: 'Erneut versuchen', onPress: fn(), testID: 'r'},
    secondary: undefined,
  },
};
