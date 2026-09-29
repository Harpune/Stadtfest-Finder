import type {Meta, StoryObj} from '@storybook/react-native';
import React, {useState} from 'react';
import {View} from 'react-native';
import {fn} from 'storybook/test';

import {FilterButton} from '../FilterButton/FilterButton';
import {SearchBar, SearchBarProps} from './SearchBar';

function Stateful(props: SearchBarProps) {
  const [value, setValue] = useState(props.value);
  return (
    <View style={{flexDirection: 'row'}}>
      <SearchBar {...props} value={value} onChangeText={setValue} />
    </View>
  );
}

const meta = {
  title: 'Suche/SearchBar',
  component: SearchBar,
  args: {value: '', onChangeText: fn(), testID: 'story.search'},
  render: args => <Stateful {...args} />,
} satisfies Meta<typeof SearchBar>;

export default meta;
type Story = StoryObj<typeof meta>;

export const Empty: Story = {};
export const WithText: Story = {args: {value: 'Aalen'}};
export const WithFilterButton: Story = {
  args: {
    trailing: (
      <FilterButton
        activeCount={2}
        onPress={() => undefined}
        testID="story.f"
      />
    ),
  },
};
export const OnSurface: Story = {args: {variant: 'surface'}};
