import type {Meta, StoryObj} from '@storybook/react-native';
import {fn} from 'storybook/test';

import {ResponseBanner} from './ResponseBanner';

const meta = {
  title: 'Einladungen/ResponseBanner',
  component: ResponseBanner,
  args: {status: 'accepted', onChange: fn(), testID: 'story.response'},
} satisfies Meta<typeof ResponseBanner>;

export default meta;
type Story = StoryObj<typeof meta>;

export const Accepted: Story = {};
export const Declined: Story = {args: {status: 'declined'}};
export const Disabled: Story = {args: {disabled: true}};
