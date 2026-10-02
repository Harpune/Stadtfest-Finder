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
  | 'chevronDown'
  | 'chevronLeft'
  | 'share'
  | 'calendar'
  | 'clock'
  | 'ticket'
  | 'navigation'
  | 'userPlus'
  | 'users'
  | 'train'
  | 'parking'
  | 'globe'
  | 'arrowUpRight'
  | 'shield'
  | 'more'
  | 'pin'
  | 'grip'
  | 'chevronRight';

export interface IconProps {
  name: IconName;
  size?: number;
  /** Defaults to the primary text color. */
  color?: string;
  strokeWidth?: number;
  /** Fill of closed shapes (e.g. the active heart); outline only by default. */
  fill?: string;
}

/** Outline icons (stroke 2, round caps) as in the design reference. */
export function Icon({
  name,
  size = 22,
  color,
  strokeWidth = 2,
  fill = 'none',
}: IconProps) {
  const theme = useTheme();
  const stroke = color ?? theme.colors.onSurface;
  const common = {
    stroke,
    strokeWidth,
    strokeLinecap: 'round' as const,
    strokeLinejoin: 'round' as const,
    fill,
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
    case 'shield':
      return (
        <>
          <Path d="M12 3l7 3v5c0 4.4-3 8.3-7 10-4-1.7-7-5.6-7-10V6z" {...c} />
          <Polyline points="9,12 11,14 15,10" {...c} />
        </>
      );
    case 'more':
      return (
        <>
          <Circle cx={6} cy={12} r={1.2} {...c} fill={c.stroke} />
          <Circle cx={12} cy={12} r={1.2} {...c} fill={c.stroke} />
          <Circle cx={18} cy={12} r={1.2} {...c} fill={c.stroke} />
        </>
      );
    case 'grip':
      return (
        <>
          {[9, 15].flatMap(x =>
            [6, 12, 18].map(y => (
              <Circle
                key={`${x}-${y}`}
                cx={x}
                cy={y}
                r={1.4}
                {...c}
                fill={c.stroke}
              />
            )),
          )}
        </>
      );
    case 'chevronRight':
      return <Polyline points="9 6 15 12 9 18" {...c} />;
    case 'pin':
      return (
        <>
          <Path d="M12 22s7-6.2 7-12a7 7 0 0 0-14 0c0 5.8 7 12 7 12z" {...c} />
          <Circle cx={12} cy={10} r={2.6} {...c} />
        </>
      );
    case 'chevronDown':
      return <Polyline points="6,9 12,15 18,9" {...c} />;
    case 'chevronLeft':
      return <Polyline points="15,5 8,12 15,19" {...c} />;
    case 'share':
      return (
        <>
          <Polyline points="8,7 12,3 16,7" {...c} />
          <Line x1={12} y1={3} x2={12} y2={15} {...c} />
          <Path d="M5 12v7a2 2 0 0 0 2 2h10a2 2 0 0 0 2-2v-7" {...c} />
        </>
      );
    case 'calendar':
      return (
        <>
          <Rect x={4} y={5} width={16} height={15} rx={2} {...c} />
          <Line x1={4} y1={10} x2={20} y2={10} {...c} />
          <Line x1={9} y1={3} x2={9} y2={7} {...c} />
          <Line x1={15} y1={3} x2={15} y2={7} {...c} />
        </>
      );
    case 'clock':
      return (
        <>
          <Circle cx={12} cy={12} r={8.5} {...c} />
          <Polyline points="12,7.5 12,12 15,14" {...c} />
        </>
      );
    case 'ticket':
      return (
        <Path
          d="M4 8V6h16v2a2.5 2.5 0 0 0 0 5v2H4v-2a2.5 2.5 0 0 0 0-5z"
          {...c}
        />
      );
    case 'navigation':
      return <Path d="M4 11l16-7-7 16-2-7-7-2z" {...c} />;
    case 'userPlus':
      return (
        <>
          <Circle cx={10} cy={8} r={3.5} {...c} />
          <Path d="M3 20c0-3.6 3.1-6 7-6s7 2.4 7 6" {...c} />
          <Line x1={19} y1={8} x2={19} y2={14} {...c} />
          <Line x1={16} y1={11} x2={22} y2={11} {...c} />
        </>
      );
    case 'users':
      return (
        <>
          <Circle cx={9} cy={8} r={3.5} {...c} />
          <Path d="M2.5 20c0-3.6 2.9-6 6.5-6s6.5 2.4 6.5 6" {...c} />
          <Path
            d="M16 4.5a3.5 3.5 0 0 1 0 7M18 14.5c2.1.8 3.5 2.9 3.5 5.5"
            {...c}
          />
        </>
      );
    case 'train':
      return (
        <>
          <Rect x={6} y={3} width={12} height={14} rx={3} {...c} />
          <Line x1={6} y1={11} x2={18} y2={11} {...c} />
          <Line x1={8} y1={21} x2={10} y2={17} {...c} />
          <Line x1={16} y1={21} x2={14} y2={17} {...c} />
        </>
      );
    case 'parking':
      return (
        <>
          <Rect x={4} y={4} width={16} height={16} rx={3} {...c} />
          <Path d="M10 16V8h3a2.5 2.5 0 0 1 0 5h-3" {...c} />
        </>
      );
    case 'globe':
      return (
        <>
          <Circle cx={12} cy={12} r={8.5} {...c} />
          <Line x1={3.5} y1={12} x2={20.5} y2={12} {...c} />
          <Path
            d="M12 3.5c2.5 2.6 3.5 5.4 3.5 8.5s-1 5.9-3.5 8.5c-2.5-2.6-3.5-5.4-3.5-8.5s1-5.9 3.5-8.5z"
            {...c}
          />
        </>
      );
    case 'arrowUpRight':
      return (
        <>
          <Line x1={7} y1={17} x2={17} y2={7} {...c} />
          <Polyline points="9,7 17,7 17,15" {...c} />
        </>
      );
  }
}
