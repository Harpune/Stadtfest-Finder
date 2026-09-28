/**
 * App theme built from the generated design tokens (00-docs/15-design/design/).
 * Components must take colors, radii and spacing from here - never hard-code them.
 */
import {designTokens} from './generated/tokens';

export type ColorScheme = 'dark' | 'light';

const {color, radius, motion} = designTokens;

function colorsFor(scheme: ColorScheme) {
  const c = color[scheme];
  return {
    ...c.brand,
    ...c.status,
    ...c.surface,
    mod: c.moderator,
    category: color.category,
  };
}

export type ThemeColors = ReturnType<typeof colorsFor>;

/** Spacing scale from the design reference (page margin 16, drawer 20). */
export const spacing = {
  xxs: 4,
  xs: 6,
  s: 8,
  sm: 10,
  m: 12,
  ml: 14,
  l: 16,
  lx: 18,
  xl: 22,
  xxl: 24,
  page: 16,
  drawer: 20,
} as const;

/** Font families as registered with expo-font in the root layout. */
export const fonts = {
  display: 'YoungSerif_400Regular',
  light: 'Outfit_300Light',
  regular: 'Outfit_400Regular',
  medium: 'Outfit_500Medium',
  semibold: 'Outfit_600SemiBold',
  bold: 'Outfit_700Bold',
} as const;

/** Minimum touch target (design reference: all touch targets >= 44 pt). */
export const MIN_TOUCH_TARGET = 44;

export interface Theme {
  scheme: ColorScheme;
  colors: ThemeColors;
  radius: typeof radius;
  motion: typeof motion;
  spacing: typeof spacing;
  fonts: typeof fonts;
  shadow: {floating: object; toast: object};
}

export function createTheme(scheme: ColorScheme): Theme {
  const dark = scheme === 'dark';
  return {
    scheme,
    colors: colorsFor(scheme),
    radius,
    motion,
    spacing,
    fonts,
    shadow: {
      floating: {
        shadowColor: dark ? '#000000' : '#231A2E',
        shadowOpacity: dark ? 0.4 : 0.14,
        shadowRadius: dark ? 12 : 10,
        shadowOffset: {width: 0, height: dark ? 8 : 6},
        elevation: 8,
      },
      toast: {
        shadowColor: '#000000',
        shadowOpacity: 0.3,
        shadowRadius: 15,
        shadowOffset: {width: 0, height: 10},
        elevation: 12,
      },
    },
  };
}

export const themes: Record<ColorScheme, Theme> = {
  dark: createTheme('dark'),
  light: createTheme('light'),
};
