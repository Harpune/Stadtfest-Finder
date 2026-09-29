import type {Meta, StoryObj} from '@storybook/react-native';
import {fn} from 'storybook/test';

import {PlaceSuggestion} from './PlaceSuggestion';

const meta = {
  title: 'Suche/PlaceSuggestion',
  component: PlaceSuggestion,
  args: {label: 'Zu Nürnberg springen', onPress: fn(), testID: 'story.place'},
} satisfies Meta<typeof PlaceSuggestion>;

export default meta;
type Story = StoryObj<typeof meta>;

export const City: Story = {};
export const PostalCode: Story = {args: {label: 'Zu 89073 Ulm springen'}};
export const LongName: Story = {
  args: {label: 'Zu Rothenburg ob der Tauber und Umgebung springen'},
};
