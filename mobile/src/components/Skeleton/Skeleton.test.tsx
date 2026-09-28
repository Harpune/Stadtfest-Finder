import {screen} from '@testing-library/react-native';
import React from 'react';

import {themes} from '@/theme';
import {renderWithProviders} from '@/test-utils';

import {Skeleton} from './Skeleton';
import {Spinner} from '../Spinner/Spinner';

describe('Skeleton and Spinner', () => {
  it('renders a skeleton in the skeleton color and hides it from screen readers', async () => {
    await renderWithProviders(<Skeleton testID="skel" height={20} />, {
      scheme: 'light',
    });
    const skeleton = screen.getByTestId('skel', {includeHiddenElements: true});
    expect(skeleton).toHaveStyle({
      backgroundColor: themes.light.colors.skeleton,
      height: 20,
    });
    expect(skeleton.props.accessibilityElementsHidden).toBe(true);
  });

  it('renders an accessible spinner', async () => {
    await renderWithProviders(<Spinner testID="spin" />);
    expect(screen.getByRole('progressbar')).toBeOnTheScreen();
  });
});
