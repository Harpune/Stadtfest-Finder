import React from 'react';
import {
  Text as RNText,
  TextProps as RNTextProps,
  TextStyle,
} from 'react-native';

import {Theme, useTheme} from '@/theme';

export type TextVariant =
  | 'displayXL'
  | 'displayL'
  | 'displayM'
  | 'displayS'
  | 'body'
  | 'bodyStrong'
  | 'meta'
  | 'caption'
  | 'label'
  | 'micro';

export type TextTone =
  | 'default'
  | 'muted'
  | 'faint'
  | 'primary'
  | 'secondary'
  | 'error'
  | 'onPrimary'
  | 'mod';

export interface TextProps extends RNTextProps {
  variant?: TextVariant;
  tone?: TextTone;
}

function variantStyle(theme: Theme, variant: TextVariant): TextStyle {
  const {fonts} = theme;
  switch (variant) {
    case 'displayXL':
      return {fontFamily: fonts.display, fontSize: 36, lineHeight: 39};
    case 'displayL':
      return {fontFamily: fonts.display, fontSize: 28, lineHeight: 32};
    case 'displayM':
      return {fontFamily: fonts.display, fontSize: 22, lineHeight: 27};
    case 'displayS':
      return {fontFamily: fonts.display, fontSize: 17, lineHeight: 22};
    case 'body':
      return {fontFamily: fonts.regular, fontSize: 15, lineHeight: 23};
    case 'bodyStrong':
      return {fontFamily: fonts.semibold, fontSize: 15, lineHeight: 23};
    case 'meta':
      return {fontFamily: fonts.regular, fontSize: 13, lineHeight: 18};
    case 'caption':
      return {fontFamily: fonts.regular, fontSize: 12, lineHeight: 16};
    case 'label':
      return {
        fontFamily: fonts.semibold,
        fontSize: 13,
        letterSpacing: 0.78,
        textTransform: 'uppercase',
      };
    case 'micro':
      return {fontFamily: fonts.medium, fontSize: 11, lineHeight: 14};
  }
}

function toneColor(theme: Theme, tone: TextTone): string {
  const c = theme.colors;
  switch (tone) {
    case 'default':
      return c.onSurface;
    case 'muted':
      return c.onSurfaceMuted;
    case 'faint':
      return c.onSurfaceFaint;
    case 'primary':
      return c.primaryText;
    case 'secondary':
      return c.secondaryText;
    case 'error':
      return c.error;
    case 'onPrimary':
      return c.onPrimary;
    case 'mod':
      return c.mod.text;
  }
}

/** Themed text with the typography scale from the design reference. */
export function Text({variant = 'body', tone, style, ...rest}: TextProps) {
  const theme = useTheme();
  const defaultTone: TextTone = variant === 'label' ? 'muted' : 'default';
  return (
    <RNText
      style={[
        variantStyle(theme, variant),
        {color: toneColor(theme, tone ?? defaultTone)},
        style,
      ]}
      {...rest}
    />
  );
}
