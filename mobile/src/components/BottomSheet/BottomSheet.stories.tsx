import type {Meta, StoryObj} from '@storybook/react-native';
import React, {useState} from 'react';
import {View} from 'react-native';
import {fn} from 'storybook/test';

import {Button} from '../Button/Button';
import {Text} from '../Text/Text';
import {BottomSheet} from './BottomSheet';

const meta = {
  title: 'Basis/BottomSheet',
  component: BottomSheet,
  args: {visible: true, onClose: fn(), title: 'Filter', testID: 'story.sheet'},
} satisfies Meta<typeof BottomSheet>;

export default meta;
type Story = StoryObj<typeof meta>;

function Toggle(args: React.ComponentProps<typeof BottomSheet>) {
  const [open, setOpen] = useState(false);
  return (
    <View>
      <Button
        label="Sheet öffnen"
        onPress={() => setOpen(true)}
        testID="open"
      />
      <BottomSheet {...args} visible={open} onClose={() => setOpen(false)}>
        <Text>Inhalt</Text>
      </BottomSheet>
    </View>
  );
}

export const Open: Story = {
  render: args => (
    <BottomSheet {...args}>
      <Text>Inhalt</Text>
    </BottomSheet>
  ),
};
export const WithFooter: Story = {
  render: args => (
    <BottomSheet
      {...args}
      footer={
        <Button
          label="8 Feste anzeigen"
          onPress={() => undefined}
          testID="f"
          style={{flex: 1}}
        />
      }
    >
      <Text>Inhalt</Text>
    </BottomSheet>
  ),
};
export const Interactive: Story = {render: args => <Toggle {...args} />};
