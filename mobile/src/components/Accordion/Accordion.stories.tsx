import type {Meta, StoryObj} from '@storybook/react-native';
import React from 'react';
import {fn} from 'storybook/test';

import {Text} from '../Text/Text';
import {Accordion} from './Accordion';

const meta = {
  title: 'Basis/Accordion',
  component: Accordion,
  args: {
    title: 'Weitere Filter (optional)',
    summary: 'Zeitraum, Kategorie, Umkreis, Schwerpunkt',
    expanded: false,
    onToggle: fn(),
    accent: 'mod',
    testID: 'story.accordion',
    children: (
      <Text variant="body" tone="muted">
        Inhalt erscheint nur aufgeklappt.
      </Text>
    ),
  },
} satisfies Meta<typeof Accordion>;

export default meta;
type Story = StoryObj<typeof meta>;

export const Collapsed: Story = {};
export const Expanded: Story = {args: {expanded: true}};
export const WithActiveFilters: Story = {args: {summary: '2 Filter aktiv'}};
export const WithoutSummary: Story = {args: {summary: undefined}};
export const Disabled: Story = {args: {disabled: true}};
