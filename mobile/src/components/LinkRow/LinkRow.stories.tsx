import type {Meta, StoryObj} from '@storybook/react-native';
import {fn} from 'storybook/test';

import {LinkRow} from './LinkRow';

const meta = {
  title: 'Detail/LinkRow',
  component: LinkRow,
  args: {
    icon: 'globe',
    label: 'Offizielle Website',
    value: 'oktoberfest.de',
    onPress: fn(),
    testID: 'story.link',
  },
} satisfies Meta<typeof LinkRow>;

export default meta;
type Story = StoryObj<typeof meta>;

export const Default: Story = {};
export const WithoutValue: Story = {args: {value: undefined}};
