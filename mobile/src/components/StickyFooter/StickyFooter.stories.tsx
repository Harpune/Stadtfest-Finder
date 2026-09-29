import type {Meta, StoryObj} from '@storybook/react-native';
import React from 'react';
import {View} from 'react-native';

import {Button} from '../Button/Button';
import {StickyFooter} from './StickyFooter';

const meta = {
  title: 'Detail/StickyFooter',
  component: StickyFooter,
} satisfies Meta<typeof StickyFooter>;

export default meta;
type Story = StoryObj<typeof meta>;

function Footer({inviteDisabled}: {inviteDisabled?: boolean}) {
  return (
    <View style={{height: 200}}>
      <StickyFooter>
        <Button
          label="Route starten"
          onPress={() => undefined}
          testID="r"
          style={{flex: 1}}
        />
        <Button
          label="Einladen"
          variant="secondary"
          disabled={inviteDisabled}
          onPress={() => undefined}
          testID="i"
        />
      </StickyFooter>
    </View>
  );
}

export const Default: Story = {render: () => <Footer />};
export const InviteDisabled: Story = {render: () => <Footer inviteDisabled />};
