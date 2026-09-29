import type {Meta, StoryObj} from '@storybook/react-native';
import React from 'react';
import {fn} from 'storybook/test';

import {Button} from '../Button/Button';
import {Skeleton} from '../Skeleton/Skeleton';
import {Text} from '../Text/Text';
import {SideDrawer} from './SideDrawer';

const meta = {
  title: 'Navigation/SideDrawer',
  component: SideDrawer,
  args: {visible: true, onClose: fn(), testID: 'story.drawer'},
} satisfies Meta<typeof SideDrawer>;

export default meta;
type Story = StoryObj<typeof meta>;

export const Default: Story = {
  args: {
    children: (
      <>
        <Text variant="displayL">Deine Festsaison auf einen Blick</Text>
        <Button
          label="Anmelden oder registrieren"
          onPress={fn()}
          testID="story.login"
        />
      </>
    ),
  },
};

export const WithFooter: Story = {
  args: {
    children: <Text variant="displayL">Deine Festsaison</Text>,
    footer: (
      <Text variant="bodyStrong" tone="secondary">
        Abmelden
      </Text>
    ),
  },
};

export const Loading: Story = {
  args: {children: <Skeleton width="80%" height={24} />},
};
