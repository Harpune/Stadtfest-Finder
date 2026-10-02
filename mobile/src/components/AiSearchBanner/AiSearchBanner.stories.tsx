import type {Meta, StoryObj} from '@storybook/react-native';
import {fn} from 'storybook/test';

import {AiSearchBanner} from './AiSearchBanner';

const meta = {
  title: 'Moderation/AiSearchBanner',
  component: AiSearchBanner,
  args: {
    state: 'running',
    text: 'Suche läuft für 73430 Aalen …',
    onReview: fn(),
    onRetry: fn(),
    onDismiss: fn(),
    testID: 'story.aiBanner',
  },
} satisfies Meta<typeof AiSearchBanner>;

export default meta;
type Story = StoryObj<typeof meta>;

export const Running: Story = {};
export const Found: Story = {
  args: {state: 'found', text: '3 neue Entwürfe aus der Suche für 73430'},
};
export const Nothing: Story = {
  args: {
    state: 'nothing',
    text: 'Keine neuen Feste für 73430 gefunden · 2 schon bekannt',
  },
};
export const Failed: Story = {
  args: {state: 'failed', text: 'Suche fehlgeschlagen'},
};
