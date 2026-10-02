import type {Meta, StoryObj} from '@storybook/react-native';
import React, {useState} from 'react';
import {View} from 'react-native';

import {ModCategoryRow} from '../ModCategoryRow/ModCategoryRow';
import {SortableList} from './SortableList';

interface Item {
  id: string;
  name: string;
  emoji: string;
  color: string;
}

const ITEMS: Item[] = [
  {id: 'a', name: 'Stadtfest', emoji: '🎪', color: '#FFB547'},
  {id: 'b', name: 'Volksfest & Kirmes', emoji: '🎡', color: '#FF6B8B'},
  {id: 'c', name: 'Weihnachtsmarkt', emoji: '🎄', color: '#5EEAD4'},
];

function Demo({enabled}: {enabled: boolean}) {
  const [items, setItems] = useState(ITEMS);
  return (
    <View style={{padding: 16}}>
      <SortableList
        items={items}
        keyOf={item => item.id}
        rowHeight={76}
        gap={10}
        enabled={enabled}
        onReorder={keys =>
          setItems(keys.map(key => items.find(item => item.id === key)!))
        }
        renderRow={(item, handle) => (
          <ModCategoryRow
            name={item.name}
            emoji={item.emoji}
            color={item.color}
            meta="3 Feste"
            handle={handle}
            onPress={() => undefined}
            testID={`story.sortable.${item.id}`}
          />
        )}
        testID="story.sortable"
      />
    </View>
  );
}

const meta = {
  title: 'Basis/SortableList',
  component: Demo,
  args: {enabled: true},
} satisfies Meta<typeof Demo>;

export default meta;
type Story = StoryObj<typeof meta>;

export const Sortable: Story = {};
export const ReadOnly: Story = {args: {enabled: false}};
