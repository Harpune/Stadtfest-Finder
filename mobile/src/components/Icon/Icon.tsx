import React from 'react';
import Svg, {Circle, Line, Path, Polyline, Rect} from 'react-native-svg';

import {useTheme} from '@/theme';

export type IconName =
  | 'search'
  | 'sliders'
  | 'close'
  | 'plus'
  | 'minus'
  | 'locate'
  | 'map'
  | 'list'
  | 'heart'
  | 'user'
  | 'chevronDown';

export interface IconProps {
  name: IconName;
  size?: number;
  /** Defaults to the primary text color. */
  color?: string;
  strokeWidth?: number;
}

/** Outline icons (stroke 2, round caps) as in the design reference. */
export function Icon({name, size = 22, color, strokeWidth = 2}: IconProps) {
  const theme = useTheme();
  const stroke = color ?? theme.colors.onSurface;
  const common = {
    stroke,
    strokeWidth,
    strokeLinecap: 'round' as const,
    strokeLinejoin: 'round' as const,
    fill: 'none',
  };
  return (
    <Svg width={size} height={size} viewBox="0 0 24 24" accessible={false}>
      {renderIcon(name, common)}
    </Svg>
  );
}

type Common = {
  stroke: string;
  strokeWidth: number;
  strokeLinecap: 'round';
  strokeLinejoin: 'round';
  fill: string;
};

function renderIcon(name: IconName, c: Common) {
  switch (name) {
    case 'search':
      return (
        <>
          <Circle cx={11} cy={11} r={7} {...c} />
          <Line x1={20} y1={20} x2={16.2} y2={16.2} {...c} />
        </>
      );
    case 'sliders':
      return (
        <>
          <Line x1={4} y1={8} x2={20} y2={8} {...c} />
          <Line x1={4} y1={16} x2={20} y2={16} {...c} />
          <Circle cx={15} cy={8} r={2.4} {...c} fill={c.stroke} />
          <Circle cx={9} cy={16} r={2.4} {...c} fill={c.stroke} />
        </>
      );
    case 'close':
      return (
        <>
          <Line x1={6} y1={6} x2={18} y2={18} {...c} />
          <Line x1={18} y1={6} x2={6} y2={18} {...c} />
        </>
      );
    case 'plus':
      return (
        <>
          <Line x1={12} y1={5} x2={12} y2={19} {...c} />
          <Line x1={5} y1={12} x2={19} y2={12} {...c} />
        </>
      );
    case 'minus':
      return <Line x1={5} y1={12} x2={19} y2={12} {...c} />;
    case 'locate':
      return (
        <>
          <Circle cx={12} cy={12} r={6} {...c} />
          <Circle cx={12} cy={12} r={2} {...c} fill={c.stroke} />
          <Line x1={12} y1={2} x2={12} y2={5} {...c} />
          <Line x1={12} y1={19} x2={12} y2={22} {...c} />
          <Line x1={2} y1={12} x2={5} y2={12} {...c} />
          <Line x1={19} y1={12} x2={22} y2={12} {...c} />
        </>
      );
    case 'map':
      return (
        <>
          <Polyline
            points="3,6 9,3 15,6 21,3 21,18 15,21 9,18 3,21 3,6"
            {...c}
          />
          <Line x1={9} y1={3} x2={9} y2={18} {...c} />
          <Line x1={15} y1={6} x2={15} y2={21} {...c} />
        </>
      );
    case 'list':
      return (
        <>
          <Line x1={9} y1={6} x2={20} y2={6} {...c} />
          <Line x1={9} y1={12} x2={20} y2={12} {...c} />
          <Line x1={9} y1={18} x2={20} y2={18} {...c} />
          <Rect x={4} y={5.5} width={1} height={1} {...c} />
          <Rect x={4} y={11.5} width={1} height={1} {...c} />
          <Rect x={4} y={17.5} width={1} height={1} {...c} />
        </>
      );
    case 'heart':
      return (
        <Path
          d="M12 20s-7-4.4-7-10a4 4 0 0 1 7-2.6A4 4 0 0 1 19 10c0 5.6-7 10-7 10z"
          {...c}
        />
      );
    case 'user':
      return (
        <>
          <Circle cx={12} cy={8} r={4} {...c} />
          <Path d="M4 21c0-4 3.6-7 8-7s8 3 8 7" {...c} />
        </>
      );
    case 'chevronDown':
      return <Polyline points="6,9 12,15 18,9" {...c} />;
  }
}
