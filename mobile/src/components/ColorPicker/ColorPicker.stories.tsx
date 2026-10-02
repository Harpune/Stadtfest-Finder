import type {Meta, StoryObj} from '@storybook/react-native';
import {fn} from 'storybook/test';

import {ColorPicker} from './ColorPicker';

const meta = {
  title: 'Moderation/ColorPicker',
  component: ColorPicker,
  args: {
    options: ['#FFB547', '#FF6B8B', '#5EEAD4', '#8B9CFF', '#7ED957', '#C792EA'],
    value: '#5EEAD4',
    onChange: fn(),
    testID: 'story.colorPicker',
  },
} satisfies Meta<typeof ColorPicker>;

export default meta;
type Story = StoryObj<typeof meta>;

export const Default: Story = {};
export const Disabled: Story = {args: {disabled: true}};
