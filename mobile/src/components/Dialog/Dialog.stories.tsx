import type {Meta, StoryObj} from '@storybook/react-native';
import React from 'react';
import {fn} from 'storybook/test';

import {TextField} from '../TextField/TextField';
import {Dialog} from './Dialog';

const meta = {
  title: 'Basis/Dialog',
  component: Dialog,
  args: {
    visible: true,
    title: 'Fest löschen?',
    text: '„Stadtfest Schwäbisch Gmünd“ wird endgültig entfernt.',
    confirmLabel: 'Endgültig löschen',
    cancelLabel: 'Abbrechen',
    onConfirm: fn(),
    onCancel: fn(),
    tone: 'danger',
    testID: 'story.dialog',
  },
} satisfies Meta<typeof Dialog>;

export default meta;
type Story = StoryObj<typeof meta>;

export const Danger: Story = {};
export const WithInput: Story = {
  args: {title: 'Fest absagen?', confirmLabel: 'Absagen und benachrichtigen'},
  render: args => (
    <Dialog {...args}>
      <TextField
        label="Grund"
        hideLabel
        placeholder="Grund (wird in der Benachrichtigung angezeigt)"
        value=""
        onChangeText={() => undefined}
        multiline
        testID="story.dialog.reason"
      />
    </Dialog>
  ),
};
export const Busy: Story = {args: {busy: true}};
export const Neutral: Story = {
  args: {
    tone: 'mod',
    title: 'Dieses Fest wurde inzwischen geändert',
    confirmLabel: 'Neu laden',
  },
};
export const ConfirmDisabled: Story = {
  args: {confirmDisabled: true, confirmLabel: 'Ersatz wählen'},
};
