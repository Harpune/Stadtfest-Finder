import type {Meta, StoryObj} from '@storybook/react-native';
import {fn} from 'storybook/test';

import {ModBanner} from './ModBanner';

const meta = {
  title: 'Moderation/ModBanner',
  component: ModBanner,
  args: {
    subtitle: 'Lena Hofmann',
    onExit: fn(),
    topInset: 0,
    testID: 'story.modBanner',
  },
} satisfies Meta<typeof ModBanner>;

export default meta;
type Story = StoryObj<typeof meta>;

export const Default: Story = {};
export const WithoutName: Story = {args: {subtitle: 'Alle Feste'}};
