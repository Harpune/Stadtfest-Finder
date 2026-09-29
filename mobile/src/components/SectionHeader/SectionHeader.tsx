import React from 'react';

import {Text} from '../Text/Text';

export interface SectionHeaderProps {
  title: string;
  testID?: string;
}

/** Section heading of the detail page (Serif 21). */
export function SectionHeader({title, testID}: SectionHeaderProps) {
  return (
    <Text
      variant="displayM"
      accessibilityRole="header"
      testID={testID}
      style={{fontSize: 21, lineHeight: 26}}
    >
      {title}
    </Text>
  );
}
