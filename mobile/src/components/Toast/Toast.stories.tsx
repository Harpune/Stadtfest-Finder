import type {Meta, StoryObj} from '@storybook/react-native';
import React from 'react';
import {View} from 'react-native';

import {Button} from '../Button/Button';
import {useToast} from './Toast';

function ToastDemo({
  message,
  withAction,
}: {
  message: string;
  withAction: boolean;
}) {
  const toast = useToast();
  return (
    <View style={{height: 400, justifyContent: 'center'}}>
      <Button
        label="Toast zeigen"
        testID="story.toast"
        onPress={() =>
          toast(
            message,
            withAction
              ? {action: {label: 'Erneut versuchen', onPress: () => undefined}}
              : undefined,
          )
        }
      />
    </View>
  );
}

const meta = {
  title: 'Basis/Toast',
  component: ToastDemo,
  args: {message: 'Zu Favoriten hinzugefügt', withAction: false},
} satisfies Meta<typeof ToastDemo>;

export default meta;
type Story = StoryObj<typeof meta>;

export const Confirmation: Story = {};
export const Error: Story = {
  args: {message: 'Feste konnten nicht geladen werden', withAction: true},
};
